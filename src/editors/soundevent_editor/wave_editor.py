"""Waveform audio editor tab.

A lightweight WAV/MP3 editor built on pyqtgraph: waveform view with mouse
zoom/pan, a drag-select region, movable markers, a playhead, and a toolbar of
numpy DSP operations (cut/copy/paste, smooth, sharpen, volume, fade ramps).

Editing works on a float32 sample buffer of shape (N, channels). MP3 (and other
non-WAV) inputs are decoded to WAV via the bundled ffmpeg on load; saving writes
16-bit PCM WAV and persists markers as a RIFF ``cue `` chunk (the same format
CS2's own content uses for loop points).

ponytail: single edit buffer, up to 20 undo snapshots (cheap for typical clips);
switch to diff-based undo only if multi-minute stereo files make snapshots heavy.
"""
import os
import wave
import struct
import tempfile
import subprocess

import numpy as np
import pyqtgraph as pg
import imageio_ffmpeg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QFileDialog, QMessageBox, QSplitter, QTabWidget, QMenuBar,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut, QAction, QPainter, QColor, QLinearGradient, QBrush
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.editors.soundevent_editor.audio_player import compute_peak_envelope
from src.widgets.explorer.main import Explorer
from src.settings.main import get_cs2_path, get_addon_name

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_AUDIO_EXTS = (".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".wma")


# ─────────────────────────────── WAV I/O ────────────────────────────────

def _read_cue_positions(path):
    """Return a list of cue-point sample offsets from a RIFF WAV, or []."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return []
    if data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return []
    pos, out = 12, []
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"cue ":
            chunk = data[pos + 8:pos + 8 + size]
            n = struct.unpack("<I", chunk[0:4])[0]
            off = 4
            for _ in range(n):
                if off + 24 > len(chunk):
                    break
                sample_offset = struct.unpack("<I", chunk[off + 20:off + 24])[0]
                out.append(sample_offset)
                off += 24
        pos += 8 + size + (size % 2)
    return out


def load_audio(path):
    """Load any supported audio file → (samples float32 (N,ch), sample_rate, cue_positions)."""
    ext = os.path.splitext(path)[1].lower()
    src = path
    tmp = None
    if ext != ".wav":
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", path, tmp.name],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )
        src = tmp.name
    try:
        with wave.open(src, "rb") as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
        dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(sw)
        if dtype is None:
            raise ValueError(f"Unsupported sample width: {sw} bytes")
        arr = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if sw == 1:
            arr = (arr - 128.0) / 128.0
        else:
            arr /= float(np.iinfo(dtype).max)
        arr = arr.reshape(-1, ch)
        cue = _read_cue_positions(src) if ext == ".wav" else []
        return arr, sr, cue
    finally:
        if tmp is not None:
            try:
                os.remove(tmp.name)
            except OSError:
                pass


def save_wav(path, samples, sr, cue_positions=None):
    """Write float32 (N,ch) samples as 16-bit PCM WAV, with an optional cue chunk."""
    ch = samples.shape[1] if samples.ndim > 1 else 1
    int16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    data = int16.tobytes()
    fmt = struct.pack("<HHIIHH", 1, ch, sr, sr * ch * 2, ch * 2, 16)
    chunks = [(b"fmt ", fmt), (b"data", data)]
    if cue_positions:
        cue = struct.pack("<I", len(cue_positions))
        for i, p in enumerate(cue_positions, 1):
            cue += struct.pack("<II4sIII", i, p, b"data", 0, 0, p)
        chunks.append((b"cue ", cue))
    body = b""
    for cid, cdata in chunks:
        body += cid + struct.pack("<I", len(cdata)) + cdata
        if len(cdata) % 2:
            body += b"\x00"
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body)


# ─────────────────────────────── DSP ops ────────────────────────────────

def _smooth(block):
    """Moving-average low-pass (softens transients)."""
    k = np.ones(5, dtype=np.float32) / 5.0
    out = np.empty_like(block)
    for c in range(block.shape[1]):
        out[:, c] = np.convolve(block[:, c], k, mode="same")
    return out


def _sharpen(block):
    """High-boost: original + (original - smoothed)."""
    return np.clip(block + (block - _smooth(block)), -1.0, 1.0)


# ─────────────────────────────── Editor ─────────────────────────────────

def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("color: rgba(80,80,80,255);")
    return line


class _SelectViewBox(pg.ViewBox):
    """ViewBox where a left-drag paints a selection range instead of panning.
    Wheel and right-drag still zoom the time axis."""
    def __init__(self, on_drag, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_drag = on_drag

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == Qt.LeftButton:
            ev.accept()
            x0 = self.mapToView(ev.buttonDownPos()).x()
            x1 = self.mapToView(ev.pos()).x()
            self._on_drag(x0, x1)
        else:
            super().mouseDragEvent(ev, axis)


class VerticalVUMeter(QWidget):
    """Vertical dB level bar with a reference scale (0 dB top → -60 dB bottom).
    Fast attack / slow release; a peak hold line marks recent maxima."""
    _MARKS = [(0, "0"), (-6, "-6"), (-12, "-12"), (-20, "-20"), (-40, "-40"), (-60, "-60")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)
        self.setMinimumHeight(80)
        self._level = 0.0
        self._peak = 0.0

    def set_level(self, level):
        level = max(0.0, min(1.0, level))
        self._level = level if level > self._level else self._level * 0.75 + level * 0.25
        self._peak = level if level >= self._peak else max(self._level, self._peak - 0.02)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect()
        p.fillRect(r, QColor(20, 20, 22))

        pad_top, pad_bot = 8, 8
        bar_x, bar_w = 6, 18
        meter_h = r.height() - pad_top - pad_bot
        if meter_h <= 0:
            return

        # meter background channel
        p.fillRect(bar_x, pad_top, bar_w, meter_h, QColor(32, 34, 38))

        # filled level, growing up from the bottom
        fill_h = int(self._level * meter_h)
        if fill_h > 0:
            grad = QLinearGradient(0, pad_top + meter_h, 0, pad_top)  # bottom→top
            grad.setColorAt(0.0, QColor(50, 200, 90))
            grad.setColorAt(0.65, QColor(220, 200, 50))
            grad.setColorAt(1.0, QColor(230, 50, 50))
            p.fillRect(bar_x, pad_top + meter_h - fill_h, bar_w, fill_h, QBrush(grad))

        # peak-hold line
        peak_y = pad_top + int((1.0 - self._peak) * meter_h)
        if self._peak > 0.0:
            p.fillRect(bar_x, max(pad_top, peak_y - 1), bar_w, 2,
                       QColor(255, 60, 60) if self._peak >= 0.95 else QColor(255, 230, 100))

        # reference scale: ticks + dB labels to the right of the bar
        font = p.font()
        font.setPointSize(7)
        p.setFont(font)
        text_x = bar_x + bar_w + 4
        for db, label in self._MARKS:
            norm = (db + 60.0) / 60.0  # 0 dB → 1.0 (top)
            y = pad_top + int((1.0 - norm) * meter_h)
            p.setPen(QColor(70, 72, 78))
            p.drawLine(bar_x, y, bar_x + bar_w, y)
            p.setPen(QColor(140, 145, 150))
            p.drawText(text_x, y + 3, label)


class AudioDocument(QWidget):
    """Single-file waveform editor (one open audio file)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.samples = None          # float32 (N, ch)
        self.sr = 44100
        self.path = None
        self._clipboard = None       # copied (M, ch) block
        self._undo = []              # list of samples snapshots
        self._render_dirty = True    # temp playback wav needs refresh
        self._temp_wav = None
        self._markers = []           # list of pg.InfiniteLine

        self._build_ui()

        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)

        self._vu_timer = QTimer(self)
        self._vu_timer.setInterval(40)
        self._vu_timer.timeout.connect(self._update_vu)
        self._env = None
        self._env_dur = 0.0

        QShortcut(QKeySequence.Undo, self, activated=self.undo)
        QShortcut(QKeySequence("Ctrl+X"), self, activated=self.cut)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.copy)
        QShortcut(QKeySequence("Ctrl+V"), self, activated=self.paste)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.toggle_play)

    # ---- UI ----
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # File menu holds the file-level actions
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu("File")
        act_open = QAction("Open...", self, triggered=self.open_file)
        act_open.setShortcut(QKeySequence.Open)
        act_save = QAction("Save", self, triggered=self.save)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save_as = QAction("Save As...", self, triggered=self.save_as)
        file_menu.addAction(act_open)
        file_menu.addSeparator()
        file_menu.addAction(act_save)
        file_menu.addAction(act_save_as)
        root.setMenuBar(menubar)

        bar = QHBoxLayout()
        bar.setSpacing(3)

        def btn(text, slot, tip=""):
            b = QPushButton(text)
            b.setToolTip(tip or text)
            b.clicked.connect(slot)
            b.setMaximumHeight(26)
            b.setFocusPolicy(Qt.NoFocus)  # so Space/Enter don't re-trigger a button
            bar.addWidget(b)
            return b

        self.play_btn = btn("Play", self.toggle_play, "Play/Pause (Space)")
        btn("Stop", self.stop)
        bar.addWidget(_sep())
        btn("Cut", self.cut, "Cut selection (Ctrl+X)")
        btn("Copy", self.copy, "Copy selection (Ctrl+C)")
        btn("Paste", self.paste, "Paste at selection start (Ctrl+V)")
        bar.addWidget(_sep())
        btn("Zoom In", lambda: self._zoom(0.5))
        btn("Zoom Out", lambda: self._zoom(2.0))
        btn("Fit", self.zoom_fit)
        btn("Select All", self.select_all)
        bar.addWidget(_sep())
        btn("Smooth", lambda: self._apply(_smooth), "Low-pass smooth selection")
        btn("Sharpen", lambda: self._apply(_sharpen), "High-boost selection")
        btn("Vol +", lambda: self._gain(1.25), "Increase volume +25%")
        btn("Vol −", lambda: self._gain(0.8), "Decrease volume -20%")
        btn("Ramp Up", lambda: self._ramp(True), "Fade in over selection")
        btn("Ramp Down", lambda: self._ramp(False), "Fade out over selection")
        bar.addWidget(_sep())
        btn("+ Marker", self.add_marker, "Add marker at playhead")
        btn("Clear Marks", self.clear_markers)
        bar.addStretch(1)
        root.addLayout(bar)

        # Waveform plot (left) + vertical VU meter (right)
        plot_row = QHBoxLayout()
        plot_row.setSpacing(4)

        pg.setConfigOptions(antialias=True)
        self._vb = _SelectViewBox(self._set_selection)
        self.plot = pg.PlotWidget(viewBox=self._vb)
        self.plot.setBackground("#1C1C1C")
        self.plot.showGrid(x=True, y=False, alpha=0.15)
        self.plot.setYRange(-1.05, 1.05)
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setLabel("bottom", "Time", units="s")
        self.curve = self.plot.plot(pen=pg.mkPen("#4BA0F0", width=1))
        self.curve.setDownsampling(auto=True)
        self.curve.setClipToView(True)

        self.region = pg.LinearRegionItem(brush=(80, 140, 240, 40))
        self.region.setZValue(-10)
        self.plot.addItem(self.region)

        self.playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#FF5050", width=2))
        self.plot.addItem(self.playhead)

        plot_row.addWidget(self.plot, 1)
        self.vu = VerticalVUMeter()
        plot_row.addWidget(self.vu)
        root.addLayout(plot_row, 1)

        self.status = QLabel("Drop an audio file here, or use File ▸ Open. "
                             "Left-drag the waveform to select a range.")
        self.status.setStyleSheet("color:#9D9D9D; font: 9pt 'Segoe UI';")
        root.addWidget(self.status)

    def _set_selection(self, x0, x1):
        """Set the selection region from a left-drag on the waveform."""
        lo, hi = sorted((x0, x1))
        if self.samples is not None:
            dur = len(self.samples) / float(self.sr)
            lo = max(0.0, lo)
            hi = min(dur, hi)
        if hi - lo > 1e-6:
            self.region.setRegion([lo, hi])

    # ---- loading ----
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open audio file", "",
            "Audio (*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.wma)")
        if path:
            self.load(path)

    def load(self, path):
        try:
            samples, sr, cue = load_audio(path)
        except Exception as error:
            QMessageBox.critical(self, "Load failed", str(error))
            return
        self.stop()
        self.samples, self.sr, self.path = samples, sr, path
        self._undo.clear()
        self._render_dirty = True
        self.clear_markers()
        self._refresh_plot()
        self.select_all()
        self.zoom_fit()
        for pos in cue:
            self._add_marker_at(pos / float(sr))
        dur = len(samples) / float(sr)
        self.status.setText(
            f"{os.path.basename(path)}  |  {dur:.2f}s  |  {sr} Hz  |  "
            f"{samples.shape[1]} ch  |  {len(cue)} marker(s)")

    def _mono(self):
        return self.samples.mean(axis=1) if self.samples.ndim > 1 else self.samples

    def _refresh_plot(self):
        if self.samples is None:
            self.curve.setData([])
            return
        t = np.arange(len(self.samples)) / float(self.sr)
        self.curve.setData(t, self._mono())
        self._render_dirty = True

    # ---- selection / zoom ----
    def _sel(self):
        """Selected sample range [i0, i1); whole buffer if region collapsed."""
        if self.samples is None:
            return 0, 0
        x0, x1 = self.region.getRegion()
        i0 = max(0, int(x0 * self.sr))
        i1 = min(len(self.samples), int(x1 * self.sr))
        if i1 - i0 < 1:
            return 0, len(self.samples)
        return i0, i1

    def select_all(self):
        if self.samples is not None:
            self.region.setRegion([0, len(self.samples) / float(self.sr)])

    def _zoom(self, factor):
        self.plot.getViewBox().scaleBy((factor, 1.0))

    def zoom_fit(self):
        if self.samples is not None:
            self.plot.setXRange(0, len(self.samples) / float(self.sr), padding=0.02)

    # ---- edit primitives ----
    def _push_undo(self):
        if self.samples is not None:
            self._undo.append(self.samples.copy())
            if len(self._undo) > 20:
                self._undo.pop(0)

    def undo(self):
        if self._undo:
            self.samples = self._undo.pop()
            self._refresh_plot()
            self.status.setText("Undo")

    def _apply(self, fn):
        if self.samples is None:
            return
        i0, i1 = self._sel()
        self._push_undo()
        self.samples[i0:i1] = fn(self.samples[i0:i1])
        self._refresh_plot()

    def _gain(self, factor):
        self._apply(lambda b: np.clip(b * factor, -1.0, 1.0))

    def _ramp(self, up):
        def fn(block):
            n = len(block)
            ramp = np.linspace(0.0, 1.0, n) if up else np.linspace(1.0, 0.0, n)
            return block * ramp[:, None]
        self._apply(fn)

    def cut(self):
        if self.samples is None:
            return
        i0, i1 = self._sel()
        self._clipboard = self.samples[i0:i1].copy()
        self._push_undo()
        self.samples = np.concatenate([self.samples[:i0], self.samples[i1:]], axis=0)
        self._refresh_plot()
        self.select_all()

    def copy(self):
        if self.samples is None:
            return
        i0, i1 = self._sel()
        self._clipboard = self.samples[i0:i1].copy()
        self.status.setText(f"Copied {i1 - i0} samples")

    def paste(self):
        if self.samples is None or self._clipboard is None:
            return
        if self._clipboard.shape[1] != self.samples.shape[1]:
            QMessageBox.warning(self, "Paste", "Channel count mismatch.")
            return
        i0, _ = self._sel()
        self._push_undo()
        self.samples = np.concatenate(
            [self.samples[:i0], self._clipboard, self.samples[i0:]], axis=0)
        self._refresh_plot()

    # ---- markers ----
    def add_marker(self):
        if self.samples is not None:
            self._add_marker_at(self.playhead.value())

    def _add_marker_at(self, seconds):
        line = pg.InfiniteLine(pos=seconds, angle=90, movable=True,
                               pen=pg.mkPen("#FFC850", width=1, style=Qt.DashLine))
        self.plot.addItem(line)
        self._markers.append(line)

    def clear_markers(self):
        for m in self._markers:
            self.plot.removeItem(m)
        self._markers = []

    def _marker_samples(self):
        return sorted(max(0, int(m.value() * self.sr)) for m in self._markers)

    # ---- saving ----
    def save(self):
        if self.samples is None:
            return
        if not self.path or not self.path.lower().endswith(".wav"):
            self.save_as()
            return
        self._write(self.path)

    def save_as(self):
        if self.samples is None:
            return
        start = os.path.splitext(self.path)[0] + ".wav" if self.path else ""
        path, _ = QFileDialog.getSaveFileName(self, "Save WAV", start, "WAV (*.wav)")
        if path:
            if not path.lower().endswith(".wav"):
                path += ".wav"
            self._write(path)
            self.path = path

    def _write(self, path):
        try:
            save_wav(path, self.samples, self.sr, self._marker_samples())
        except Exception as error:
            QMessageBox.critical(self, "Save failed", str(error))
            return
        self.status.setText(f"Saved {os.path.basename(path)}")

    # ---- playback ----
    def _render_temp(self):
        if self._temp_wav is None:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tf.close()
            self._temp_wav = tf.name
        save_wav(self._temp_wav, self.samples, self.sr)
        self._render_dirty = False
        self._env, self._env_dur = compute_peak_envelope(self._temp_wav)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            return
        if self.samples is None:
            return
        if self._render_dirty:
            self._render_temp()
            self.player.setSource(QUrl.fromLocalFile(self._temp_wav))
        self.player.play()
        self._vu_timer.start()

    def stop(self):
        self.player.stop()
        self._vu_timer.stop()
        self.vu.set_level(0.0)
        self.playhead.setValue(0)

    def _on_position(self, ms):
        self.playhead.setValue(ms / 1000.0)

    def _on_state(self, state):
        self.play_btn.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")
        if state != QMediaPlayer.PlayingState:
            self._vu_timer.stop()
            self.vu.set_level(0.0)

    def _update_vu(self):
        if self._env is None or self._env_dur <= 0:
            self.vu.set_level(0.0)
            return
        idx = int((self.player.position() / 1000.0) / self._env_dur)
        idx = max(0, min(idx, len(self._env) - 1))
        db = 20.0 * np.log10(float(self._env[idx]) + 1e-6)
        self.vu.set_level((db + 60.0) / 60.0)

    # ---- drag & drop ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(_AUDIO_EXTS):
                self.load(p)
                break


class AudioEditor(QWidget):
    """Container: an audio explorer (addon sounds) plus a tabbed set of open
    documents. Double-clicking an audio file in the explorer opens it in a tab."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)

        self.explorer = Explorer(
            tree_directory=self._addon_sounds_dir(), addon=get_addon_name(),
            editor_name="AudioEditor", parent=self, use_internal_player=False)
        self.explorer.tree.setStyleSheet("border:none")
        self.explorer.tree.doubleClicked.connect(self._on_explorer_double_click)
        splitter.addWidget(self.explorer.frame)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 820])
        root.addWidget(splitter)

    def _addon_sounds_dir(self):
        cs2 = get_cs2_path()
        if cs2 and get_addon_name():
            return os.path.join(cs2, "content", "csgo_addons", get_addon_name(), "sounds")
        return None

    def set_root(self, path):
        """Re-point the explorer at a new sounds folder (e.g. on addon switch)."""
        if not path:
            return
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        ex = self.explorer
        ex.tree_directory = path
        ex.model.setRootPath(path)
        ex.tree.setRootIndex(ex.filter_proxy_model.mapFromSource(ex.model.index(path)))

    def _on_explorer_double_click(self, index):
        source = self.explorer.filter_proxy_model.mapToSource(index)
        path = self.explorer.model.filePath(source)
        if os.path.isfile(path) and path.lower().endswith(_AUDIO_EXTS):
            self.open_document(path)

    def open_document(self, path):
        # Focus an already-open document for this file
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            existing = getattr(widget, "path", None)
            if existing and os.path.normcase(existing) == os.path.normcase(path):
                self.tabs.setCurrentIndex(i)
                return
        doc = AudioDocument()
        doc.load(path)
        if doc.samples is None:  # load failed (error already shown)
            doc.deleteLater()
            return
        idx = self.tabs.addTab(doc, os.path.basename(path))
        self.tabs.setCurrentIndex(idx)

    def _close_tab(self, index):
        widget = self.tabs.widget(index)
        try:
            widget.stop()
        except Exception:
            pass
        self.tabs.removeTab(index)
        widget.deleteLater()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(_AUDIO_EXTS):
                self.open_document(p)
