'''
Button groups
function : turn on/off several camera

== Button Layout ==
                interval_h1    width2  interval_h2
                          \    /       /            ================================\\      -------
            |   width1  |----|--|-------|                                            ||    interval_v3
     ----   +-----------+               +-----------+               +-----------+    ||     -------
  height1   |    btn    |    +--+       |    btn    |    +--+       |    btn    |    ||
       |    |           |    +--+  ---  |           |    +--+       |           |    ||
     ----   +-----------+           |   +-----------+               +-----------+    ||
  interval_v1                    interval_v2                                         ||
     ----   +-----------+           |   +-----------+               +-----------+    ||
            |    btn    |    +--+  ---  |    btn    |    +--+       |    btn    |    ||
     ||     |           |    +--+       |           |    +--+       |           |    ||
     ||     +-----------+               +-----------+               +-----------+    ||
     ||                                                                              ||
     ||     +-----------+               +-----------+               +-----------+    ||
     ||     |    btn    |    +--+       |    btn    |    +--+       |    btn    |    ||
     ||     |           |    +--+       |           |    +--+       |           |    ||
     ||     +-----------+          ---- +-----------+               +-----------+    ||
     ||                             20    |------| <-- width (CtrlButton)            ||
     ||                            ----   +------+          ---                      ||
     ||                                   |  up  |           | <- height (CtrlButton)||
     ||            115             +------+------+------+   ---                      ||
     ||<-------------------------->| left |      | right|                            ||
     ||                            +------+------+------+                            ||
     ||                                   | down |                                   ||
     ||                                   +------+   ----                            ||
     ||                                               20                             ||
      \\============================================================================//

'''

import numpy as np
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QRadioButton, QFrame

from control_thread import *
from mqtt_thread import *


class RadioButton(QRadioButton):
    signal_rbtn_checked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 20
        self.height = 20
        self.idx = -1
        self.clicked.connect(self.send_rbtn_idx)

    @pyqtSlot()
    def send_rbtn_idx(self):
        if not self.isChecked():
            self.signal_rbtn_checked.emit(self.idx)


class CamButton(QPushButton):
    status_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 80
        self.height = 20
        self.no = None
        self.setText('Cam 1: Off')
        self.RUNNING = False

    @pyqtSlot()
    def btn_clicked(self):
        if not self.RUNNING:
            self.RUNNING = True
            self.setText('Cam ' + str(self.no) + ': On')
            self.status_changed.emit(False)
        else:
            self.RUNNING = False
            self.setText('Cam ' + str(self.no) + ': Off')
            self.status_changed.emit(True)

    @pyqtSlot(bool)
    def cam_disconnected(self):
        pass


class StatusColor(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = True # True : Pause, False: Running
        self.activation = False
        self.width = 10
        self.height = 10
        self.setStyleSheet('background-color: red')

    @pyqtSlot(bool)
    def status_changed(self, status):
        self.status = status
        if self.status:
            self.setStyleSheet('background-color: red')
        else:
            self.setStyleSheet('background-color: green')


class CtrlButton(QPushButton):
    signal_dir_btn_cmd = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 50
        self.height = 50
        self.diffx = 0
        self.diffy = 0
        self.clicked.connect(self.send_diff)

    @pyqtSlot()
    def send_diff(self):
        self.signal_dir_btn_cmd.emit(self.diffx, self.diffy)


class CameraControl(QWidget):
    signal_send_cmd = pyqtSignal(int, int)

    def __init__(self, parent=None, layout_style=True):
        super().__init__(parent)
        if layout_style:
            self.joystick = Control(self) # thread
            self.setGeometry(115, 160, 150, 150)
            self.joystick.start()
            self.joystick.joystick.show()
        else:
            self.ctrl_btns = [CtrlButton(self) for _ in range(4)]


class ControlPanel(QFrame):
    signal_send_target_idx = pyqtSignal(int)
    signal_pub_cmd_msg = pyqtSignal(str) # already implemented in control_thread/Joystick - send_cmd, need to connect to mqtt_thread

    def __init__(self, num_camera, parent=None):
        super().__init__(parent)
        self.width = 400
        self.height = 40 + 100 + 20 + 150 + 20
        self.interval_v1 = 10
        self.interval_v2 = 20
        self.interval_v3 = 15
        self.interval_h1 = 5
        self.interval_h2 = 35
        self.num_camera = num_camera
        self.setGeometry(1010, 5, self.width, self.height)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.camera_status = [False for _ in range(9)]
        self.buttons = [CamButton(self) for _ in range(9)]
        self.status_colors = [StatusColor(self) for _ in range(9)]
        self.radio_btns = [RadioButton(self) for _ in range(9)]

        self.client = CLIENT() # remove

        self.joystick_usage = True
        self.target_cam = -1

        self.controller = CameraControl(self)
        self.set_buttons()

        self.client.start() # remove

    @pyqtSlot(str, int)
    def set_esp_controller_idx(self, ip_addr, idx):
        self.client.publish('server/setting', "{'ip': %s, 'idx': %d}" % (ip_addr, idx))

    @pyqtSlot(int, int) # need to change -> signal (no mqtt_client)
    def pub_msg(self, x, y):
        self.client.publish('server/cmd',
                                   "{'idx': %d, 'x': %d, 'y':%d}" % (self.joystick.joystick.target_cam, x, y))

    @pyqtSlot(int)
    def set_target(self, cam_no):
        self.target_cam = cam_no

    def set_buttons(self):
        # camera buttons
        for idx in range(9):
            width1 = self.buttons[idx].width
            height1 = self.buttons[idx].height
            width2 = self.status_colors[idx].width
            height2 = self.status_colors[idx].height
            width3 = self.radio_btns[idx].width
            height3 = self.radio_btns[idx].height
            x1 = self.interval_h1 + (width1 + self.interval_h1 + width2 + self.interval_h2) * (idx %3)
            x2 = self.interval_h1 + width1 + self.interval_h1 + (width2 + self.interval_h2 + width1 + self.interval_h1) * (idx % 3)
            x3 = x2 + 15
            y1 = 40 + self.interval_v1 + (height1 + self.interval_v1) * (idx // 3)
            y2 = 40 + self.interval_v3 + (height2 + self.interval_v2) * (idx // 3)

            self.buttons[idx].setGeometry(x1, y1, width1, height1)
            self.buttons[idx].no = idx+1
            self.buttons[idx].setText('Cam '+str(idx+1)+' : Off')
            self.status_colors[idx].setGeometry(x2, y2, width2, height2)
            self.radio_btns[idx].setGeometry(x3, y1, width3, height3)
            self.radio_btns[idx].idx = idx
            self.radio_btns[idx].signal_rbtn_checked.connect(self.set_target)

        for idx in range(self.num_camera, 9):
            self.buttons[idx].setDisabled(True)
            self.status_colors[idx].setStyleSheet('background-color: black')
            self.radio_btns[idx].setDisabled(True)

        if not self.joystick_usage:
            # Camera control buttons
            self.ctrl_btns[0].setGeometry(115 + 50, 40 + 100 + 20, 50, 50) # up
            self.ctrl_btns[0].setText('Up')
            self.ctrl_btns[1].setGeometry(115 + 50, 40 + 100 + 20 + 100, 50, 50) # down
            self.ctrl_btns[1].setText('Down')
            self.ctrl_btns[2].setGeometry(115, 40 + 100 + 20 + 50, 50, 50) # left
            self.ctrl_btns[2].setText('Left')
            self.ctrl_btns[3].setGeometry(115 + 100, 40 + 100 + 20 + 50, 50, 50) # right
            self.ctrl_btns[3].setText('Right')
        else:
            self.controller.joystick.joystick.send_cmd.connect(self.pub_msg) # need to connect with mqtt_client
