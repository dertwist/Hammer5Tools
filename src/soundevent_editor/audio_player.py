from PySide6.QtWidgets import QVBoxLayout, QPushButton, QCheckBox, QLabel, QSlider, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from src.preferences import set_config_bool, get_config_bool
from src.soundevent_editor.ui_audio_player import Ui_Form


class AudioPlayer(QWidget):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

        self.init_ui()
        self.setup_connections()
        self.filepath = None

        if file_path:
            self.set_audiopath(file_path)

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        self.loop_checkbox = QCheckBox("Loop")
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")

        self.loop_enabled = get_config_bool('SoundEventEditor', 'AudioPlayerLoop')
        self.loop_checkbox.setChecked(self.loop_enabled)

        self.layout.addWidget(self.play_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.loop_checkbox)
        self.layout.addWidget(self.timeline_slider)
        self.layout.addWidget(self.current_time_label)
        self.layout.addWidget(self.total_time_label)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)

    def setup_connections(self):
        self.play_button.clicked.connect(self.play_sound)
        self.stop_button.clicked.connect(self.stop_sound)
        self.loop_checkbox.stateChanged.connect(self.toggle_loop)
        self.timeline_slider.sliderMoved.connect(self.seek_position)
        self.audio_player.positionChanged.connect(self.update_position)
        self.audio_player.durationChanged.connect(self.update_duration)
        self.audio_player.mediaStatusChanged.connect(self.handle_media_status)
        self.timer.timeout.connect(self.update_time_labels)

    def play_sound(self):
        if self.filepath:
            self.audio_player.setSource(self.filepath)
            self.audio_player.play()
            self.timer.start()

    def set_audiopath(self, path):
        self.filepath = QUrl.fromLocalFile(path)

    def stop_sound(self):
        self.audio_player.stop()
        self.timer.stop()

    def toggle_loop(self, state):
        self.loop_enabled = state == Qt.Checked
        set_config_bool('SoundEventEditor', 'AudioPlayerLoop', self.loop_checkbox.isChecked())
        print(get_config_bool('SoundEventEditor', 'AudioPlayerLoop'))

    def seek_position(self, position):
        self.audio_player.setPosition(position)

    def update_position(self, position):
        self.timeline_slider.setValue(position)

    def update_duration(self, duration):
        self.timeline_slider.setRange(0, duration)
        self.total_time_label.setText(self.format_time(duration))

    def update_time_labels(self):
        current_time = self.audio_player.position()
        self.current_time_label.setText(self.format_time(current_time))

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia and self.loop_enabled:
            self.audio_player.setPosition(0)
            self.audio_player.play()

    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        return f"{minutes:02}:{seconds:02}"