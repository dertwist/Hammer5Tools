from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from src.settings.preferences import set_config_bool, get_config_bool
from src.soundevent_editor.ui_audio_player import Ui_Form
from PySide6.QtGui import QIcon

class AudioPlayer(QWidget):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

        self.duration = "00:00"
        self.filepath = None

        self.init_ui()
        self.setup_connections()

        if file_path:
            self.set_audiopath(file_path)

    def init_ui(self):
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")

        self.loop_enabled = get_config_bool('SoundEventEditor', 'AudioPlayerLoop', default=False)
        self.ui.loop_checkbox.setChecked(self.loop_enabled)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)

        # Set initial icon and text for play/pause button
        self.update_play_button_icon()

    def setup_connections(self):
        self.ui.play_button.clicked.connect(self.toggle_play_pause)
        self.ui.loop_checkbox.stateChanged.connect(self.toggle_loop)
        self.ui.timeline_slider.sliderMoved.connect(self.seek_position)
        self.audio_player.positionChanged.connect(self.update_position)
        self.audio_player.durationChanged.connect(self.update_duration)
        self.audio_player.mediaStatusChanged.connect(self.handle_media_status)
        self.audio_player.playbackStateChanged.connect(self.update_play_button_icon)  # Connect state change to update method
        self.timer.timeout.connect(self.update_time_labels)

    def toggle_play_pause(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            self.pause_sound()
        else:
            self.play_sound()

    def play_sound(self):
        if self.filepath:
            if self.audio_player.playbackState() == QMediaPlayer.StoppedState:
                self.audio_player.setSource(self.filepath)
            self.audio_player.play()
            self.timer.start()

    def pause_sound(self):
        self.audio_player.pause()
        self.timer.stop()

    def update_play_button_icon(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            icon = QIcon(":/valve_common/icons/tools/common/control_pause.png")
            self.ui.play_button.setText("Pause")
        else:
            icon = QIcon(":/valve_common/icons/tools/common/control_play.png")
            self.ui.play_button.setText("Play")
        self.ui.play_button.setIcon(icon)

    def set_audiopath(self, path):
        self.filepath = QUrl.fromLocalFile(path)

    def toggle_loop(self, state):
        self.loop_enabled = self.ui.loop_checkbox.isChecked()
        set_config_bool('SoundEventEditor', 'AudioPlayerLoop', self.ui.loop_checkbox.isChecked())

    def seek_position(self, position):
        self.audio_player.setPosition(position)
        # Play if the audio was paused
        if self.audio_player.playbackState() != QMediaPlayer.PlayingState:
            self.play_sound()

    def update_position(self, position):
        self.ui.timeline_slider.setValue(position)
        self.update_time_labels()

    def update_duration(self, duration):
        self.ui.timeline_slider.setRange(0, duration)
        self.duration = self.format_time(duration)
        self.update_time_labels()

    def update_time_labels(self):
        current_time = self.audio_player.position()
        self.ui.time.setText(f"{self.format_time(current_time)} : {self.duration}")

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.loop_enabled:
                self.audio_player.setPosition(0)
                self.audio_player.play()
            else:
                self.update_play_button_icon()

    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        return f"{minutes:02}:{seconds:02}"