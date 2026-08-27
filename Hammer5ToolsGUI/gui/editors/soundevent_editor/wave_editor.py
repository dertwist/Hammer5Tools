"""Waveform audio editor tab.

A lightweight WAV/MP3 editor built on pyqtgraph: waveform view with mouse
zoom/pan, a drag-select region, movable markers, a playhead, and a toolbar of
numpy DSP operations (volume, fade ramps).

Editing works on a float32 sample buffer of shape (N, channels). MP3 (and other
non-WAV) inputs are decoded to WAV via QtMultimedia's QAudioDecoder on load;
saving writes 16-bit PCM WAV and persists markers as a RIFF ``cue `` chunk (the
same format CS2's own content uses for loop points).

The editor retains up to 20 full-buffer undo snapshots.
"""
import os
import wave
import struct
import tempfile

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QFileDialog, QMessageBox, QTabWidget, QMenuBar,
    QToolBar, QToolButton, QSizePolicy, QMainWindow, QDockWidget,
    QPushButton, QStackedWidget,
)
from PySide6.QtCore import Qt, QTimer, QUrl, Signal, QSize, QEvent
from PySide6.QtGui import QKeySequence, QAction, QIcon, QPainter, QColor, QLinearGradient, QBrush, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui.editors.soundevent_editor.audio_convert import decode_to_pcm16
from gui.editors.soundevent_editor.audio_player import (
    compute_peak_envelope, DBInfoOverlay, apply_meter_gradient, meter_peak_color,
)
from gui.widgets.explorer.main import Explorer
from gui.settings.common import get_cs2_path, get_addon_name
from gui.styles import theme

_AUDIO_EXTS = (".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".wma")

# Toolbar / menu icons (resource paths from the app's compiled .qrc)
_CTRL = ":/valve_common/icons/tools/common/"
_IC = {
    "play": _CTRL + "control_play.png",
    "pause": _CTRL + "control_pause.png",
    "stop": _CTRL + "control_stop.png",
    "new": _CTRL + "new.png",
    "open": ":/icons/file_open_16dp.svg",
    "save": ":/icons/save_16dp.svg",
    "save_as": ":/icons/save_as_16dp.svg",
    "undo": ":/icons/undo_24dp.svg",
    "redo": ":/icons/redo_16dp.svg",
    "cut": ":/icons/content_cut_24dp.svg",
    "copy": ":/icons/content_copy_24dp.svg",
    "paste": ":/icons/content_paste_24dp.svg",
    "zoom_in": ":/icons/zoom_in_24dp.svg",
    "zoom_out": ":/icons/remove_24dp.svg",
    "fit": ":/icons/open_in_full_24dp.svg",
    "vol_up": ":/icons/volume_up.png",
    "vol_down": ":/icons/volume_up.png",
    "marker": ":/icons/new_label_24dp.svg",
    "clear": ":/icons/clear_all_16dp.svg",
}



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
        samples, sr = decode_to_pcm16(path)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(samples.shape[1])
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(samples.astype("<i2").tobytes())
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





def _alpha(canonical, alpha):
    """Theme colour at a given Qt alpha, for painters and pyqtgraph brushes."""
    color = theme.qcolor(canonical)
    color.setAlpha(alpha)
    return color


def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setProperty("h5Component", "soundeventSeparator")
    return line


class _SelectViewBox(pg.ViewBox):
    """ViewBox where a left-drag paints a selection range instead of panning.
    Wheel and right-drag still zoom the time axis."""
    def __init__(self, on_drag, on_click, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_drag = on_drag
        self._on_click = on_click

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == Qt.LeftButton:
            ev.accept()
            x0 = self.mapToView(ev.buttonDownPos()).x()
            x1 = self.mapToView(ev.pos()).x()
            self._on_drag(x0, x1)
        else:
            super().mouseDragEvent(ev, axis)

    def mouseClickEvent(self, ev):
        # A plain left-click (no drag) moves the playhead / seeks
        if ev.button() == Qt.LeftButton:
            ev.accept()
            self._on_click(self.mapToView(ev.pos()).x())
        else:
            super().mouseClickEvent(ev)


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
        colors = theme.get_theme()
        p.fillRect(r, QColor(colors.surface_raised))

        pad_top, pad_bot = 8, 8
        bar_x, bar_w = 6, 18
        meter_h = r.height() - pad_top - pad_bot
        if meter_h <= 0:
            return

        # meter background channel
        p.fillRect(bar_x, pad_top, bar_w, meter_h, theme.qcolor("#242428"))

        # filled level, growing up from the bottom
        fill_h = int(self._level * meter_h)
        if fill_h > 0:
            grad = QLinearGradient(0, pad_top + meter_h, 0, pad_top)  # bottom→top
            apply_meter_gradient(grad)
            p.fillRect(bar_x, pad_top + meter_h - fill_h, bar_w, fill_h, QBrush(grad))

        # peak-hold line
        peak_y = pad_top + int((1.0 - self._peak) * meter_h)
        if self._peak > 0.0:
            p.fillRect(bar_x, max(pad_top, peak_y - 1), bar_w, 2, meter_peak_color(self._peak))

        # reference scale: ticks + dB labels to the right of the bar
        font = p.font()
        font.setPointSize(7)
        p.setFont(font)
        text_x = bar_x + bar_w + 4
        for db, label in self._MARKS:
            norm = (db + 60.0) / 60.0  # 0 dB → 1.0 (top)
            y = pad_top + int((1.0 - norm) * meter_h)
            p.setPen(QColor(colors.border))
            p.drawLine(bar_x, y, bar_x + bar_w, y)
            p.setPen(QColor(colors.text_muted))
            p.drawText(text_x, y + 3, label)


class AudioDocument(QWidget):
    """Single-file waveform editor (one open audio file)."""
    dirty_changed = Signal(bool)     # unsaved-edits state changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.samples = None          # float32 (N, ch)
        self.sr = 44100
        self.path = None
        self._clipboard = None       # copied (M, ch) block
        self._undo = []              # undo snapshots (samples copies)
        self._redo = []              # redo snapshots
        self._dirty = False          # unsaved edits present
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

    # UI
    def _make_actions(self):
        """Build every command as a QAction (icon + shortcut) so the File menu and
        the toolbar share one definition. WidgetWithChildrenShortcut scopes each
        shortcut to this document, so multiple open tabs never fight over Ctrl+S."""
        def mk(text, slot, icon=None, shortcut=None, tip=None):
            a = QAction(text, self)
            if icon:
                a.setIcon(QIcon(icon))
            if shortcut:
                a.setShortcut(shortcut)
            a.setToolTip(tip or text)
            a.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            a.triggered.connect(slot)
            self.addAction(a)
            return a

        self.act_new = mk("New", lambda: self.load_blank(), _IC["new"], QKeySequence.New)
        self.act_open = mk("Open", self.open_file, _IC["open"], QKeySequence.Open)
        self.act_save = mk("Save", self.save, _IC["save"], QKeySequence("Ctrl+S"))
        self.act_save_as = mk("Save As", self.save_as, _IC["save_as"])
        self.act_play = mk("Play", self.toggle_play, _IC["play"],
                           QKeySequence(Qt.Key_Space), "Play/Pause (Space)")
        self.act_stop = mk("Stop", self.stop, _IC["stop"])
        self.act_undo = mk("Undo", self.undo, _IC["undo"], QKeySequence.Undo)
        self.act_redo = mk("Redo", self.redo, _IC["redo"], QKeySequence.Redo)
        self.act_cut = mk("Cut", self.cut, _IC["cut"], QKeySequence("Ctrl+X"))
        self.act_copy = mk("Copy", self.copy, _IC["copy"], QKeySequence("Ctrl+C"))
        self.act_paste = mk("Paste", self.paste, _IC["paste"], QKeySequence("Ctrl+V"))
        self.act_zoom_in = mk("Zoom In", lambda: self._zoom(0.5), _IC["zoom_in"])
        self.act_zoom_out = mk("Zoom Out", lambda: self._zoom(2.0), _IC["zoom_out"])
        self.act_fit = mk("Fit", self.zoom_fit, _IC["fit"])
        self.act_select_all = mk("Select All", self.select_all, None, QKeySequence.SelectAll)
        self.act_vol_up = mk("Vol +", lambda: self._gain(1.25), _IC["vol_up"],
                             None, "Increase volume +25%")
        self.act_vol_down = mk("Vol −", lambda: self._gain(0.8), _IC["vol_down"],
                               None, "Decrease volume -20%")
        self.act_ramp_up = mk("Ramp Up", lambda: self._ramp(True), None,
                              None, "Fade in over selection")
        self.act_ramp_down = mk("Ramp Down", lambda: self._ramp(False), None,
                                None, "Fade out over selection")
        self.act_marker = mk("Add Marker", self.add_marker, _IC["marker"],
                             QKeySequence("M"), "Add marker at playhead")
        self.act_clear = mk("Clear Markers", self.clear_markers, _IC["clear"])

        # Categorized menus (None = separator inside a menu). The toolbar reuses
        # this structure, one group per menu with separators between groups.
        self._menus = [
            ("File", [self.act_new, self.act_open, self.act_save, self.act_save_as]),
            ("Edit", [self.act_undo, self.act_redo, None,
                      self.act_cut, self.act_copy, self.act_paste, None,
                      self.act_select_all]),
            ("View", [self.act_zoom_in, self.act_zoom_out, self.act_fit]),
            ("Playback", [self.act_play, self.act_stop]),
            ("Effects", [self.act_vol_up, self.act_vol_down, None,
                         self.act_ramp_up, self.act_ramp_down]),
            ("Markers", [self.act_marker, self.act_clear]),
        ]
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        self._make_actions()

        # Categorized menu bar: File / Edit / View / Playback / Effects / Markers
        menubar = QMenuBar(self)
        menubar.setProperty("h5Component", "soundeventWaveMenuBar")
        for name, acts in self._menus:
            m = menubar.addMenu(name)
            for a in acts:
                if a is None:
                    m.addSeparator()
                else:
                    m.addAction(a)
        root.setMenuBar(menubar)

        # Compact toolbar mirroring the same actions (one group per menu).
        # Colours/borders match the SoundEvent editor (#2e2e2e, 2px grey border,
        # #515965 hover) but with tighter padding so the buttons stay small.
        toolbar = QToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(14, 14))
        toolbar.setProperty("h5Component", "soundeventWaveToolbar")
        # Actions excluded from the toolbar (stay accessible via menus/hotkeys)
        toolbar_excluded = {
            self.act_new, self.act_open, self.act_save, self.act_save_as,
            self.act_undo, self.act_redo,
            self.act_cut, self.act_copy, self.act_paste, self.act_select_all,
            self.act_zoom_in, self.act_zoom_out,
        }
        first = True
        for name, acts in self._menus:
            items = [a for a in acts if a is not None and a not in toolbar_excluded]
            if not items:
                continue
            if not first:
                toolbar.addSeparator()
            first = False
            for a in items:
                toolbar.addAction(a)
        for b in toolbar.findChildren(QToolButton):
            b.setFocusPolicy(Qt.NoFocus)  # so Space/Enter don't re-trigger a button
        root.addWidget(toolbar)

        # Waveform plot (left) + vertical VU meter & reference guide (right)
        plot_row = QHBoxLayout()
        plot_row.setSpacing(4)

        pg.setConfigOptions(antialias=True)
        self._vb = _SelectViewBox(self._set_selection, self._seek_to)
        self.plot = pg.PlotWidget(viewBox=self._vb)
        self.plot.showGrid(x=True, y=False, alpha=0.15)
        self.plot.setYRange(-1.05, 1.05)
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setLabel("bottom", "Time", units="s")
        self.curve = self.plot.plot()
        self.curve.setDownsampling(auto=True)
        self.curve.setClipToView(True)

        self.region = pg.LinearRegionItem()
        self.region.setZValue(-10)
        self.plot.addItem(self.region)

        self.playhead = pg.InfiniteLine(pos=0, angle=90)
        self.playhead.setZValue(20)
        self.plot.addItem(self.playhead)
        self._apply_plot_theme()

        plot_row.addWidget(self.plot, 1)

        # Right column: vertical VU meter + dB reference-guide button
        right = QVBoxLayout()
        right.setSpacing(4)
        self.vu = VerticalVUMeter()
        right.addWidget(self.vu, 1)
        self.info_button = QToolButton()
        self.info_button.setToolTip("Show dB Level Reference Guide")
        self.info_button.setFixedSize(22, 22)
        self.info_button.setFocusPolicy(Qt.NoFocus)
        info_icon = QIcon(":/valve_common/icons/tools/common/icon_info_sm.png")
        if info_icon.isNull():
            self.info_button.setText("ℹ")
        else:
            self.info_button.setIcon(info_icon)
        self.info_button.setProperty("h5Component", "soundeventInfoButton")
        self._info_overlay = DBInfoOverlay(self)
        self.info_button.clicked.connect(self._toggle_info)
        right.addWidget(self.info_button, 0, Qt.AlignHCenter)
        plot_row.addLayout(right)

        root.addLayout(plot_row, 1)

        self.status = QLabel("Drop an audio file here, or use File ▸ Open. "
                             "Single-click to move the play line; left-drag to select.")
        self.status.setProperty("h5Component", "soundeventWaveStatus")
        root.addWidget(self.status)

    def _apply_plot_theme(self):
        """Repaint pyqtgraph items from the active theme.

        pyqtgraph pens and brushes are plain objects, not stylesheet-driven, so
        they have to be re-made whenever the theme changes.
        """
        self.plot.setBackground(theme.get_theme().background)
        self.curve.setPen(pg.mkPen(theme.color("#4ba0f0"), width=1))
        self.region.setBrush(_alpha("#4ba0f0", 40))
        self.playhead.setPen(pg.mkPen(theme.color("#ff5050"), width=2))
        for marker in self._markers:
            self._style_marker(marker)

    def changeEvent(self, event):
        super().changeEvent(event)
        # A live theme switch repolishes every widget, which lands here.
        if event.type() == QEvent.StyleChange:
            self._apply_plot_theme()

    def showEvent(self, event):
        super().showEvent(event)
        # Qt only repolishes widgets it has already shown, so a document built
        # before the switch catches up here instead.
        self._apply_plot_theme()

    def _seek_to(self, x):
        """Single-click on the waveform → move the playhead / seek playback."""
        if self.samples is None:
            return
        dur = len(self.samples) / float(self.sr)
        x = max(0.0, min(dur, x))
        self.playhead.setValue(x)
        self.player.setPosition(int(x * 1000))

    def _toggle_info(self):
        if self._info_overlay.isVisible():
            self._info_overlay.hide()
            return
        self._info_overlay.adjustSize()
        tr = self.info_button.mapToGlobal(self.info_button.rect().topRight())
        self._info_overlay.move(tr.x() - self._info_overlay.width(),
                                tr.y() - self._info_overlay.height() - 4)
        self._info_overlay.show()

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
            "Audio (*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.wma)"
        )
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
        self._redo.clear()
        self._set_dirty(False)
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

    def load_blank(self, duration_s=1.0, sr=44100, channels=2):
        self.stop()
        n_samples = int(duration_s * sr)
        self.samples = np.zeros((n_samples, channels), dtype=np.float32)
        self.sr = sr
        self.path = None
        self._undo.clear()
        self._redo.clear()
        self._set_dirty(False)
        self._render_dirty = True
        self.clear_markers()
        self._refresh_plot()
        self.select_all()
        self.zoom_fit()
        self.status.setText(f"Untitled  |  {duration_s:.2f}s  |  {sr} Hz  |  {channels} ch  |  Blank")

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

    # ---- undo / redo / dirty ----
    def _set_dirty(self, value):
        if value != self._dirty:
            self._dirty = value
            self.dirty_changed.emit(value)

    def _push_undo(self):
        """Snapshot before a mutation; clears the redo stack and marks dirty."""
        if self.samples is not None:
            self._undo.append(self.samples.copy())
            if len(self._undo) > 20:
                self._undo.pop(0)
            self._redo.clear()
            self._set_dirty(True)

    def undo(self):
        if not self._undo:
            return
        self._redo.append(self.samples.copy())
        self.samples = self._undo.pop()
        self._refresh_plot()
        self._set_dirty(True)
        self.status.setText("Undo")

    def redo(self):
        if not self._redo:
            return
        self._undo.append(self.samples.copy())
        self.samples = self._redo.pop()
        self._refresh_plot()
        self._set_dirty(True)
        self.status.setText("Redo")

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

    def add_marker(self):
        if self.samples is not None:
            self._add_marker_at(self.playhead.value())

    def _style_marker(self, line):
        line.setPen(pg.mkPen(theme.color("#ffc850"), width=1, style=Qt.DashLine))
        line.label.setColor(theme.qcolor("#ffc850"))
        line.label.fill = pg.mkBrush(_alpha(theme.get_theme().surface_raised, 200))
        line.label.update()

    def _add_marker_at(self, seconds):
        line = pg.InfiniteLine(
            pos=seconds, angle=90, movable=True, label="{value:.2f}s",
            labelOpts={"position": 0.92, "movable": True})
        line.setZValue(15)
        self._style_marker(line)
        self.plot.addItem(line)
        self._markers.append(line)

    def clear_markers(self):
        for m in self._markers:
            self.plot.removeItem(m)
        self._markers = []

    def _marker_samples(self):
        return sorted(max(0, int(m.value() * self.sr)) for m in self._markers)

    # saving
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
        path, _ = QFileDialog.getSaveFileName(
            self, "Save WAV", start, "WAV (*.wav)"
        )
        if path:
            if not path.lower().endswith(".wav"):
                path += ".wav"
            self.path = path
            self._write(path)

    def _write(self, path):
        try:
            save_wav(path, self.samples, self.sr, self._marker_samples())
        except Exception as error:
            QMessageBox.critical(self, "Save failed", str(error))
            return
        self._set_dirty(False)
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
        playing = state == QMediaPlayer.PlayingState
        self.act_play.setText("Pause" if playing else "Play")
        self.act_play.setIcon(QIcon(_IC["pause"] if playing else _IC["play"]))
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


class AudioEditor(QMainWindow):
    """Container: a dockable audio explorer (addon sounds) plus a tabbed set of
    open documents. Double-clicking an audio file in the explorer opens it in a
    document tab."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setContentsMargins(6, 6, 6, 6)  # breathing room around the main widget

        # Central Stack: Page 0 = Empty State, Page 1 = Document Tabs
        self.central_stack = QStackedWidget()

        # Page 0: Empty State View
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QPixmap(":/icons/soundviewer.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Open an audio file or create a new document")
        title_lbl.setProperty("h5Component", "emptyStateTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Select an audio file in the Audio Explorer on the left, open an existing file, or create a new audio document.")
        desc_lbl.setProperty("h5Component", "emptyStateDescription")
        desc_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(desc_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setAlignment(Qt.AlignCenter)

        btn_open = QPushButton("Open File...")
        btn_open.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        btn_open.setProperty("h5Component", "legacyButton")
        btn_open.setFixedHeight(26)
        btn_open.clicked.connect(self.open_file_dialog)
        btn_row.addWidget(btn_open)

        btn_new = QPushButton("Create New...")
        btn_new.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        btn_new.setProperty("h5Component", "legacyButton")
        btn_new.setFixedHeight(26)
        btn_new.clicked.connect(self.new_document)
        btn_row.addWidget(btn_new)

        empty_layout.addLayout(btn_row)
        self.central_stack.addWidget(self.empty_state_widget)

        # Page 1: Multi-Document Tab Widget
        from gui.widgets.document_tab import DocumentTabWidget
        self.tabs = DocumentTabWidget()
        self.tabs.set_new_tab_tooltip("Create New Audio Document (Ctrl+N)")
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.new_tab_requested.connect(self.new_document)
        self.new_tab_btn = self.tabs.new_tab_btn

        self.central_stack.addWidget(self.tabs)
        self.setCentralWidget(self.central_stack)

        # Shortcuts
        new_act = QAction("New Document", self)
        new_act.setShortcut(QKeySequence.New)
        new_act.triggered.connect(self.new_document)
        self.addAction(new_act)

        open_act = QAction("Open Document", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self.open_file_dialog)
        self.addAction(open_act)

        # Audio explorer in a dockable panel
        self.explorer = Explorer(
            tree_directory=self._addon_sounds_dir(), addon=get_addon_name(),
            editor_name="AudioEditor", parent=self, use_internal_player=True)
        # use_internal_player=True routes the Explorer's play-on-click through its
        # play_sound signal instead of spawning its own player. We connect nothing
        # to that signal, so selecting a file (incl. the auto-selection at load)
        # makes no sound — only double-click opens a document tab.
        self.explorer.tree.setProperty("h5Component", "soundeventBorderlessExplorer")
        self.explorer.tree.doubleClicked.connect(self._on_explorer_double_click)

        explorer_border = QWidget()
        explorer_border.setProperty("h5Component", "soundeventExplorerBorder")
        _border_lay = QVBoxLayout(explorer_border)
        _border_lay.setContentsMargins(0, 0, 0, 0)
        _border_lay.addWidget(self.explorer.frame)

        self._explorer_dock = QDockWidget("Audio Explorer", self)
        self._explorer_dock.setObjectName("audio_explorer_dock")
        self._explorer_dock.setWidget(explorer_border)
        self._explorer_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._explorer_dock)

        # Match the SmartProp editor's dock/tab-bar styling
        from gui.common import set_qdock_tab_style
        set_qdock_tab_style(self.findChildren)

        self._update_view_stack()

    def _update_view_stack(self):
        if self.tabs.count() > 0:
            self.central_stack.setCurrentWidget(self.tabs)
        else:
            self.central_stack.setCurrentWidget(self.empty_state_widget)

    def new_document(self):
        doc = AudioDocument()
        doc.load_blank()
        idx = self.tabs.addTab(doc, "Untitled")
        doc.dirty_changed.connect(lambda dirty, d=doc: self._mark_tab(d, dirty))
        self.tabs.setCurrentIndex(idx)
        self._update_view_stack()

    def open_file_dialog(self):
        sounds_dir = self._addon_sounds_dir() or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", sounds_dir,
            "Audio Files (*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.wma);;All Files (*)"
        )
        if path:
            self.open_document(path)

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
                self._update_view_stack()
                return
        doc = AudioDocument()
        doc.load(path)
        if doc.samples is None:  # load failed (error already shown)
            doc.deleteLater()
            return
        idx = self.tabs.addTab(doc, os.path.basename(path))
        doc.dirty_changed.connect(lambda dirty, d=doc: self._mark_tab(d, dirty))
        self.tabs.setCurrentIndex(idx)
        self._update_view_stack()

    def _mark_tab(self, doc, dirty):
        """Prefix the tab title with '*' while the document has unsaved edits."""
        i = self.tabs.indexOf(doc)
        if i >= 0:
            name = os.path.basename(doc.path or "Untitled")
            self.tabs.setTabText(i, ("*" + name) if dirty else name)

    def unsaved_files(self):
        """(label, save_callable) for every audio tab with unsaved edits."""
        files = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if getattr(widget, "_dirty", False):
                files.append((widget.path or "Untitled", widget.save))
        return files

    def _close_tab(self, index):
        widget = self.tabs.widget(index)
        if getattr(widget, "_dirty", False):
            name = os.path.basename(widget.path or "audio")
            resp = QMessageBox.question(
                self, "Unsaved changes",
                f"'{name}' has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save)
            if resp == QMessageBox.Cancel:
                return
            if resp == QMessageBox.Save:
                widget.save()
                if widget._dirty:  # save cancelled or failed → abort close
                    return
        try:
            widget.stop()
        except Exception:
            pass
        self.tabs.removeTab(index)
        widget.deleteLater()
        self._update_view_stack()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(_AUDIO_EXTS):
                self.open_document(p)
