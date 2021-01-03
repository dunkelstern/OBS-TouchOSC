import sys

from PySide2.QtCore import (
    QSettings,
    QTimer
)
from PySide2.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox
)
from PySide2.QtGui import (
    QIcon, QIntValidator
)

from obs.service import OBSRemote
from utils.resource_path import resource_path


class MainWindow(QWidget):

    def __init__(self, appctx):
        super().__init__()

        self.appctx = appctx
        self.obs = None
        self.tick_timer = QTimer()
        self.tick_timer.setInterval(200)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start()

        company = 'dunkelstern' if sys.platform != 'darwin' else 'de.dunkelstern'
        self.settings = QSettings(company, 'OBSTouchOSC')

        self.init_ui()
        self.load_settings()

    def load_settings(self):
        self.obs_host.setText(self.settings.value('obs/host', '127.0.0.1'))
        self.obs_port.setText(self.settings.value('obs/port', '4444'))
        self.auth_password.setText(self.settings.value('obs/password', ''))
        self.touchosc_host.setText(self.settings.value('touchosc/host', ''))
        self.touchosc_port.setText(self.settings.value('touchosc/port', '9000'))
        self.osc_port.setText(self.settings.value('osc/port', '8000'))

    def save_settings(self):
        self.settings.setValue('obs/host', self.obs_host.text())
        self.settings.setValue('obs/port', self.obs_port.text())
        self.settings.setValue('obs/password', self.auth_password.text())
        self.settings.setValue('touchosc/host', self.touchosc_host.text())
        self.settings.setValue('touchosc/port', self.touchosc_port.text())
        self.settings.setValue('osc/port', self.osc_port.text())
        self.settings.sync()

    def init_ui(self):
        self.vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # Set layout
        self.setLayout(self.vbox)

        # OBS Settings
        group_frame = QGroupBox("OBS")
        group_frame.setLayout(QVBoxLayout())

        label = QLabel("Hostname/IP")
        group_frame.layout().addWidget(label)
        self.obs_host = QLineEdit()
        group_frame.layout().addWidget(self.obs_host)

        label = QLabel("Port")
        group_frame.layout().addWidget(label)
        self.obs_port = QLineEdit()
        self.obs_port.setValidator(QIntValidator(1024, 65535))
        group_frame.layout().addWidget(self.obs_port)

        label = QLabel("Password")
        group_frame.layout().addWidget(label)
        self.auth_password = QLineEdit()
        group_frame.layout().addWidget(self.auth_password)

        self.hbox.addWidget(group_frame)

        # TouchOSC Settings
        group_frame = QGroupBox("TouchOSC")
        group_frame.setLayout(QVBoxLayout())

        label = QLabel("Hostname/IP")
        group_frame.layout().addWidget(label)
        self.touchosc_host = QLineEdit()
        group_frame.layout().addWidget(self.touchosc_host)

        label = QLabel("Port")
        group_frame.layout().addWidget(label)
        self.touchosc_port = QLineEdit()
        self.touchosc_port.setValidator(QIntValidator(1024, 65535))
        group_frame.layout().addWidget(self.touchosc_port)

        self.hbox.addWidget(group_frame)

        # OSC Settings
        group_frame = QGroupBox("OSC")
        group_frame.setLayout(QVBoxLayout())

        label = QLabel("Port")
        group_frame.layout().addWidget(label)
        self.osc_port = QLineEdit()
        self.osc_port.setValidator(QIntValidator(1024, 65535))
        group_frame.layout().addWidget(self.osc_port)

        self.hbox.addWidget(group_frame)

        # Add all to layout
        self.vbox.addLayout(self.hbox)

        # Start button
        icon = QIcon(resource_path('icons/play.png'))
        self.start_button = QPushButton(icon, "Start")
        self.start_button.pressed.connect(self.start_pressed)
        self.vbox.addWidget(self.start_button)

        self.setWindowTitle('OBS TouchOSC')

    def enable_controls(self, enabled):
        for i in range(0, self.hbox.count()):
            control = self.hbox.itemAt(i).widget()
            control.setEnabled(enabled)

    def stop_pressed(self):
        # stop server
        self.obs.stop()
        self.obs = None

        # enable all controls
        self.enable_controls(True)

        # switch to play button
        icon = QIcon(resource_path('icons/play.png'))
        self.start_button.setIcon(icon)
        self.start_button.setText('Start')
        self.start_button.pressed.disconnect()
        self.start_button.pressed.connect(self.start_pressed)

    def start_pressed(self):
        # validate all inputs
        for not_empty in [self.obs_host, self.touchosc_host]:
            if not_empty.text() == '':
                not_empty.setFocus()
                return
        for valid in [self.obs_port, self.touchosc_port, self.osc_port]:
            if not valid.hasAcceptableInput():
                valid.setFocus()
                return

        # Save settings
        self.save_settings()

        # disable all controls
        self.enable_controls(False)

        # switch to stop button
        icon = QIcon(resource_path('icons/stop.png'))
        self.start_button.setIcon(icon)
        self.start_button.setText('Stop')
        self.start_button.pressed.disconnect()
        self.start_button.pressed.connect(self.stop_pressed)

        # Start server

        self.obs = OBSRemote(
            int(self.osc_port.text()),
            self.touchosc_host.text(),
            int(self.touchosc_port.text()),
            self.obs_host.text(),
            int(self.obs_port.text()),
            password=self.auth_password.text()
        )
        self.obs.start()

    def tick(self):
        if self.obs:
            self.obs.tick()