import os
import wave
import tempfile
import numpy as np
from PySide6.QtWidgets import QLabel, QWidget, QSizePolicy, QToolButton, QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import QTimer, QUrl, Signal, Qt, QPoint
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QIcon, QPainter, QColor, QLinearGradient, QBrush, QFont
from src.settings.main import set_settings_bool, get_settings_bool
from src.editors.soundevent_editor.ui_audio_player import Ui_Form


def compute_peak_envelope(path, frame_ms=30):
    """Return (envelope, frame_seconds) where envelope is a 0..1 linear peak per
    time frame, computed from a PCM WAV. Returns (None, 0.0) for anything that
    isn't a readable 8/16/32-bit PCM WAV (e.g. mp3) so the meter just stays idle."""
    try:
        with wave.open(path, 'rb') as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
    except Exception:
        return None, 0.0
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(sw)
    if dtype is None or not raw:
        return None, 0.0
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if sw == 1:  # 8-bit PCM is unsigned, centred at 128
        samples = (samples - 128.0) / 128.0
    else:
        samples /= float(np.iinfo(dtype).max)
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1)
    frame_len = max(1, int(sr * frame_ms / 1000))
    n = len(samples) // frame_len
    if n == 0:
        return None, 0.0
    env = np.abs(samples[:n * frame_len].reshape(n, frame_len)).max(axis=1)
    return env, frame_ms / 1000.0


class DBInfoOverlay(QFrame):
    """Floating overlay popup displaying dB Reference Guide matching #1D1D1F background styling."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("dbInfoOverlay")
        self.setStyleSheet(
            "QFrame#dbInfoOverlay {"
            "  background-color: #1D1D1F;"
            "  border: 1px solid #3D3D42;"
            "  border-radius: 4px;"
            "}"
            "QLabel {"
            "  color: #E3E3E3;"
            "  font: 9pt \"Segoe UI\";"
            "}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header: Title + Close Button
        header = QHBoxLayout()
        title = QLabel("dB Reference Guide", self)
        title.setStyleSheet("font-weight: bold; font-size: 10pt; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QToolButton(self)
        close_btn.setText("✕")
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            "QToolButton { color: #9D9D9D; border: none; font-size: 10px; background-color: transparent; padding: 2px; }"
            "QToolButton:hover { color: #FFFFFF; background-color: #3D3D42; border-radius: 2px; }"
        )
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # dB Guide Items
        info_items = [
            ("0 dBFS", "Digital Maximum Ceiling (Avoid Clipping)", "#E53935"),
            ("-3 to -6 dB", "SFX Peak Target (Gunshots, Impacts, Explosions)", "#FFB300"),
            ("-12 to -18 dB", "Nominal Operating Level (Dialogue, Footsteps)", "#4CAF50"),
            ("-24 to -18 dB", "Ambient Background / Room Tone", "#29B6F6"),
            ("-60 dB", "Noise Floor Cutoff / Silence Level", "#8E8E93"),
        ]

        for db_val, desc, color in info_items:
            row = QHBoxLayout()
            row.setSpacing(8)

            badge = QLabel(db_val, self)
            badge.setFixedWidth(84)
            badge.setStyleSheet(
                f"background-color: #27272A; color: {color}; font-weight: bold; "
                f"border-radius: 3px; padding: 2px 4px; font-size: 8.5pt;"
            )
            badge.setAlignment(Qt.AlignCenter)
            row.addWidget(badge)

            desc_label = QLabel(desc, self)
            desc_label.setStyleSheet("color: #CCCCCC; font-size: 8.5pt;")
            row.addWidget(desc_label)

            layout.addLayout(row)


class VUMeter(QWidget):
    """Horizontal dB level bar with decibel scale labels: green→yellow→red, fast attack / slow release."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 22)
        self.setMaximumHeight(26)
        self._level = 0.0  # 0..1 displayed (maps -60 dB .. 0 dB)
        self._peak = 0.0
        self._peak_decay = 0.0

    def set_level(self, level):
        level = max(0.0, min(1.0, level))
        # fast attack, slow release — classic VU ballistics
        self._level = level if level > self._level else self._level * 0.75 + level * 0.25
        if level > self._peak:
            self._peak = level
            self._peak_decay = 0.0
        else:
            self._peak_decay += 0.05
            self._peak = max(self._level, self._peak - self._peak_decay * 0.04)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect()

        # Background (#1D1D1F)
        p.fillRect(r, QColor(29, 29, 31))

        meter_h = 9
        meter_y = 13
        meter_w = r.width()

        # Draw dB scale labels on top (-50, -40, -30, -20, -12, -6, 0)
        font = p.font()
        font.setPointSize(7)
        p.setFont(font)

        markers = [(-50, "-50"), (-40, "-40"), (-30, "-30"), (-20, "-20"), (-12, "-12"), (-6, "-6"), (0, "0dB")]
        for db, label in markers:
            norm = (db + 60.0) / 60.0
            x = int(norm * meter_w)
            x_text = max(0, x - (8 if not label.endswith("dB") else 12))
            if x_text + 18 > meter_w:
                x_text = meter_w - 18
            p.setPen(QColor(140, 145, 150))
            p.drawText(x_text, 10, label)
            p.setPen(QColor(60, 60, 65))
            p.drawLine(x, 11, x, meter_y)

        # Meter background bar
        p.fillRect(0, meter_y, meter_w, meter_h, QColor(36, 36, 40))

        # Filled level bar
        w = int(meter_w * self._level)
        if w > 0:
            grad = QLinearGradient(0, 0, meter_w, 0)
            grad.setColorAt(0.0, QColor(50, 200, 90))
            grad.setColorAt(0.65, QColor(220, 200, 50))
            grad.setColorAt(1.0, QColor(230, 50, 50))
            p.fillRect(0, meter_y, w, meter_h, QBrush(grad))

        # Peak indicator line
        peak_x = int(meter_w * self._peak)
        if peak_x > 0 and peak_x <= meter_w:
            peak_color = QColor(255, 60, 60) if self._peak >= 0.95 else QColor(255, 230, 100)
            p.fillRect(max(0, peak_x - 1), meter_y, 2, meter_h, peak_color)


class WaveformWidget(QWidget):
    """Interactive waveform display replacing standard timeline slider.
    Displays symmetric waveform peaks, active play position line, mouse click/drag seeking, and hover cursor."""
    seek_requested = Signal(int)  # seek position in ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(24)
        self.setMaximumHeight(32)
        self.setMouseTracking(True)

        self._waveform = None  # numpy array of normalized 0..1 peaks
        self._position_ms = 0
        self._duration_ms = 0

        self._hover_x = -1
        self._is_hovering = False

    def set_waveform(self, env):
        self._waveform = env
        self.update()

    def set_position(self, ms: int):
        self._position_ms = max(0, ms)
        self.update()

    def set_duration(self, ms: int):
        self._duration_ms = max(0, ms)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._seek_from_pos(event.position().x())

    def mouseMoveEvent(self, event):
        self._hover_x = event.position().x()
        if event.buttons() & Qt.LeftButton:
            self._seek_from_pos(event.position().x())
        self.update()

    def enterEvent(self, event):
        self._is_hovering = True
        self.update()

    def leaveEvent(self, event):
        self._is_hovering = False
        self._hover_x = -1
        self.update()

    def _seek_from_pos(self, x):
        if self.width() <= 0 or self._duration_ms <= 0:
            return
        ratio = max(0.0, min(1.0, x / float(self.width())))
        seek_ms = int(ratio * self._duration_ms)
        self.seek_requested.emit(seek_ms)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cy = h / 2.0

        # Background (#1D1D1F)
        p.fillRect(self.rect(), QColor(29, 29, 31))

        # Calculate progress ratio
        progress_ratio = 0.0
        if self._duration_ms > 0:
            progress_ratio = max(0.0, min(1.0, self._position_ms / float(self._duration_ms)))
        playhead_x = int(progress_ratio * w)

        # Draw waveform
        if self._waveform is not None and len(self._waveform) > 0:
            env = self._waveform
            num_samples = len(env)
            bar_count = min(w, 300)
            bar_width = max(1.0, w / float(bar_count))

            for i in range(bar_count):
                x_center = (i + 0.5) * bar_width
                x_left = int(i * bar_width)

                # Sample peak in this bin
                idx_start = int(i * num_samples / float(bar_count))
                idx_end = max(idx_start + 1, int((i + 1) * num_samples / float(bar_count)))
                peak = float(np.max(env[idx_start:idx_end])) if idx_start < num_samples else 0.0

                amp_h = max(2.0, peak * (h - 6.0))
                y_top = cy - (amp_h / 2.0)

                # Color: played part vs unplayed part
                if x_center <= playhead_x:
                    col = QColor(60, 160, 240)  # Active blue/cyan accent for played section
                else:
                    col = QColor(75, 82, 95)    # Subtle gray for unplayed section

                p.fillRect(x_left, int(y_top), max(1, int(bar_width - 1)), int(amp_h), col)
        else:
            # Fallback center line if no waveform data (e.g. idle or mp3)
            p.setPen(QColor(70, 75, 85))
            p.drawLine(0, int(cy), w, int(cy))

        # Playhead vertical line
        if self._duration_ms > 0:
            p.fillRect(max(0, playhead_x - 1), 0, 2, h, QColor(255, 75, 75))

        # Hover indicator line
        if self._is_hovering and 0 <= self._hover_x <= w:
            p.fillRect(int(self._hover_x), 0, 1, h, QColor(255, 255, 255, 120))


class AudioPlayer(QWidget):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Set background style to #1D1D1F
        self.setStyleSheet("QWidget { background-color: #1D1D1F; }")
        self.ui.content.setStyleSheet("QFrame#content { background-color: #1D1D1F; border: none; }")

        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

        self.filepath = None
        self.temp_file_name = None
        self.duration = "00:00"

        self._env = None
        self._env_frame_dur = 0.0

        # Replace timeline_slider with WaveformWidget
        self.ui.timeline_slider.hide()
        self.waveform_widget = WaveformWidget(self.ui.content)
        self.waveform_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Row 1 (horizontalLayout): time label -> waveform_widget -> play_button -> loop_checkbox
        self.ui.horizontalLayout.removeWidget(self.ui.timeline_slider)
        self.ui.horizontalLayout.insertWidget(1, self.waveform_widget)

        # Row 2 (verticalLayout): VU Meter + Info Button in a QHBoxLayout
        row2_widget = QWidget(self)
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setContentsMargins(0, 2, 0, 0)
        row2_layout.setSpacing(4)

        self.vu_meter = VUMeter(row2_widget)
        self.vu_meter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row2_layout.addWidget(self.vu_meter)

        self.info_button = QToolButton(row2_widget)
        self.info_button.setToolTip("Show dB Level Reference Guide")
        self.info_button.setFixedSize(22, 22)
        icon = QIcon(":/valve_common/icons/tools/common/icon_info_sm.png")
        if not icon.isNull():
            self.info_button.setIcon(icon)
        else:
            self.info_button.setText("ℹ")
        self.info_button.setStyleSheet(
            "QToolButton {"
            "  background-color: #1D1D1F;"
            "  border: 1px solid #333336;"
            "  border-radius: 2px;"
            "  color: #E3E3E3;"
            "}"
            "QToolButton:hover {"
            "  background-color: #414956;"
            "  color: #FFFFFF;"
            "}"
        )
        row2_layout.addWidget(self.info_button)

        self.ui.verticalLayout.addWidget(row2_widget)

        # DB Info Overlay instance
        self.info_overlay = DBInfoOverlay(self)
        self.info_button.clicked.connect(self.toggle_info_overlay)

        self.vu_timer = QTimer(self)
        self.vu_timer.setInterval(40)
        self.vu_timer.timeout.connect(self._update_vu)

        self.init_ui()
        self.setup_connections()

        if file_path:
            self.set_audiopath(file_path)

    def toggle_info_overlay(self):
        """Toggle inline floating overlay panel anchored to the info button."""
        if self.info_overlay.isVisible():
            self.info_overlay.hide()
        else:
            from PySide6.QtWidgets import QApplication
            self.info_overlay.adjustSize()
            btn_pos = self.info_button.mapToGlobal(QPoint(0, 0))
            overlay_h = self.info_overlay.sizeHint().height()
            overlay_w = self.info_overlay.sizeHint().width()

            # Align right edge of overlay with info button
            x = btn_pos.x() + self.info_button.width() - overlay_w
            y = btn_pos.y() - overlay_h - 4

            # Screen bounds clamping to prevent left/right/top clipping
            screen = QApplication.screenAt(btn_pos)
            if not screen:
                screen = QApplication.primaryScreen()
            if screen:
                s_rect = screen.availableGeometry()
                if x < s_rect.left() + 8:
                    x = s_rect.left() + 8
                elif x + overlay_w > s_rect.right() - 8:
                    x = s_rect.right() - overlay_w - 8

                if y < s_rect.top() + 8:
                    y = btn_pos.y() + self.info_button.height() + 4

            self.info_overlay.move(x, y)
            self.info_overlay.show()

    def init_ui(self):
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")

        self.loop_enabled = get_settings_bool('SoundEventEditor', 'AudioPlayerLoop', default=False)
        self.ui.loop_checkbox.setChecked(self.loop_enabled)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)

        self.update_play_button_icon()

    def setup_connections(self):
        self.ui.play_button.clicked.connect(self.toggle_play_pause)
        self.ui.loop_checkbox.stateChanged.connect(self.toggle_loop)
        self.waveform_widget.seek_requested.connect(self.seek_position)
        self.audio_player.positionChanged.connect(self.update_position)
        self.audio_player.durationChanged.connect(self.update_duration)
        self.audio_player.mediaStatusChanged.connect(self.handle_media_status)
        self.audio_player.playbackStateChanged.connect(self.update_play_button_icon)
        self.timer.timeout.connect(self.update_time_labels)

    def toggle_play_pause(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            self.pause_sound()
        else:
            self.play_sound()

    def play_sound(self):
        if self.temp_file_name and os.path.exists(self.temp_file_name):
            if self.audio_player.playbackState() == QMediaPlayer.StoppedState:
                pass
            self.audio_player.play()
            self.timer.start()
            self.vu_timer.start()

    def pause_sound(self):
        self.audio_player.pause()
        self.timer.stop()
        self.vu_timer.stop()
        self.vu_meter.set_level(0.0)

    def _update_vu(self):
        """Sample the precomputed envelope at the current playback position."""
        if self._env is None or self._env_frame_dur <= 0:
            self.vu_meter.set_level(0.0)
            return
        idx = int((self.audio_player.position() / 1000.0) / self._env_frame_dur)
        idx = max(0, min(idx, len(self._env) - 1))
        peak = float(self._env[idx])
        # linear peak → dB → 0..1 over a -60..0 dB range
        db = 20.0 * np.log10(peak + 1e-6)
        self.vu_meter.set_level((db + 60.0) / 60.0)

    def update_play_button_icon(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            icon = QIcon(":/valve_common/icons/tools/common/control_pause.png")
            self.ui.play_button.setText("Pause")
        else:
            icon = QIcon(":/valve_common/icons/tools/common/control_play.png")
            self.ui.play_button.setText("Play")
        self.ui.play_button.setIcon(icon)

    def set_audiopath(self, path):
        try:
            with open(path, "rb") as source_file:
                data = source_file.read()

            if self.temp_file_name and os.path.exists(self.temp_file_name):
                os.remove(self.temp_file_name)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(data)
                tmp.flush()
                self.temp_file_name = tmp.name

            self.audio_player.setSource(QUrl.fromLocalFile(self.temp_file_name))
            self.filepath = path
            # Envelope from the real source file (mp3 → None, meter stays idle)
            self._env, self._env_frame_dur = compute_peak_envelope(path)
            self.waveform_widget.set_waveform(self._env)

        except Exception as e:
            print(f"Error loading file '{path}': {e}")
            self.temp_file_name = None
            self.filepath = None
            self._env, self._env_frame_dur = None, 0.0
            self.waveform_widget.set_waveform(None)

    def toggle_loop(self, state):
        self.loop_enabled = self.ui.loop_checkbox.isChecked()
        set_settings_bool('SoundEventEditor', 'AudioPlayerLoop', self.loop_enabled)

    def seek_position(self, position):
        self.audio_player.setPosition(position)
        if self.audio_player.playbackState() != QMediaPlayer.PlayingState:
            self.play_sound()

    def update_position(self, position):
        self.waveform_widget.set_position(position)
        self.update_time_labels()

    def update_duration(self, duration):
        self.waveform_widget.set_duration(duration)
        self.duration = self.format_time(duration)
        self.update_time_labels()

    def update_time_labels(self):
        current_time = self.audio_player.position()
        self.ui.time.setText(f"{self.format_time(current_time)} : {self.duration}")

    def handle_media_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            if self.loop_enabled:
                self.audio_player.setPosition(0)
                self.audio_player.play()
            else:
                self.update_play_button_icon()
                self.vu_timer.stop()
                self.vu_meter.set_level(0.0)

    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        return f"{minutes:02}:{seconds:02}"

    def closeEvent(self, event):
        self.pause_sound()
        if self.info_overlay:
            self.info_overlay.close()

        if self.temp_file_name and os.path.exists(self.temp_file_name):
            os.remove(self.temp_file_name)
        super().closeEvent(event)