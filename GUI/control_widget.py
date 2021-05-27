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
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QPushButton, QRadioButton, QLabel, QFrame
from control_thread import *
from mqtt_thread import *

class RadioButton(QRadioButton):
    signal_rbtn_checked = pyqtSignal(int)

    def __init__(self, parent, idx):
        super().__init__(parent)
        self.width = 20
        self.height = 20
        self.idx = idx
        self.clicked.connect(self.send_rbtn_idx)

    def send_rbtn_idx(self):
        print('[RBTN] Clicked')
        if self.isChecked():
            self.signal_rbtn_checked.emit(self.idx)


class CamButton(QPushButton):
    status_changed = pyqtSignal(int, bool)

    def __init__(self, parent, idx):
        super().__init__(parent)
        self.idx = idx
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
            self.status_changed.emit(self.idx, False)
        else:
            self.RUNNING = False
            self.setText('Cam ' + str(self.no) + ': Off')
            self.status_changed.emit(self.idx, True)

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

    @pyqtSlot(int, bool)
    def status_changed(self, idx, status):
        self.status = status
        if self.status:
            self.setStyleSheet('background-color: red')
        else:
            self.setStyleSheet('background-color: green')


class CameraControl(QWidget):
    signal_send_cmd = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.joystick = Control(self) # thread
        self.setGeometry(115, 160, 150, 150)


class PanelParamInit(QThread):
    signal_request_panel_param = pyqtSignal()
    signal_send_panel_param = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.param_loaded = False

    @pyqtSlot(object)
    def resend_panel_param(self, param):
        self.param_loaded=True
        self.signal_send_panel_param.emit(param)

    def run(self):
        while not self.param_loaded:
            self.signal_request_panel_param.emit()
            time.sleep(0.3)
        print('[CONTROLLER-init] Parameter-set received')


class ControlPanel(QFrame):
    signal_send_target_idx = pyqtSignal(int)
    signal_send_status_changed = pyqtSignal(int, bool)
    signal_control_init_chk = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_info = None
        self.esp_idx = None
        self.width = None
        self.height = None
        self.interval_v1 = None
        self.interval_v2 = None
        self.interval_v3 = None
        self.interval_h1 = None
        self.interval_h2 = None
        self.num_camera = None
        self.use_joystick = True
        self.camera_status = [False for _ in range(9)]
        self.buttons = [CamButton(self, i) for i in range(9)]
        self.status_colors = [StatusColor(self) for _ in range(9)]
        self.radio_btns = [RadioButton(self, i) for i in range(9)]
        self.controller = CameraControl(self)
        self.initializer = PanelParamInit()
        self.initializer.signal_send_panel_param.connect(self.set_param)
        #self.controller.joystick.joystick.send_cmd.connect(self.mqtt_client.msg_publish)

    def chk_esp_idx(self, camera_info):
        esp_idx = []
        for idx in range(len(camera_info)):
            if camera_info['mode'].iloc[idx] == 'ESP':
                esp_idx.append(idx)
        self.esp_idx = esp_idx

    @pyqtSlot(object)
    def set_param(self, param):
        time.sleep(0.4)
        self.camera_info = param['camera_info']
        self.num_camera = param['num_camera']
        self.width = param['width']
        self.height = param['height']
        self.interval_v1 = param['interval_v1']
        self.interval_v2 = param['interval_v2']
        self.interval_v3 = param['interval_v3']
        self.interval_h1 = param['interval_h1']
        self.interval_h2 = param['interval_h2']
        print('[CONTROLLER] Parameter-set loaded')
        self.initializer.working=False
        self.initializer.quit()
        time.sleep(0.3)

        self.setGeometry(1010, 5, self.width, self.height)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.chk_esp_idx(self.camera_info)
        self.set_buttons()

    @pyqtSlot(int)
    def set_target(self, cam_no):
        self.target_cam = cam_no
        self.signal_send_target_idx.emit(self.target_cam)

    @pyqtSlot(int, bool)
    def status_changed(self, int, bool):
        self.signal_send_status_changed.emit(int, bool)

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
            #self.radio_btns[idx].signal_rbtn_checked.connect(self.set_target)

            if idx in self.esp_idx:
                self.radio_btns[idx].setEnabled(True)
                self.radio_btns[idx].signal_rbtn_checked.connect(self.set_target)
            else:
                self.radio_btns[idx].setDisabled(True)

        for idx in range(9):
            if idx >= self.num_camera:
                self.buttons[idx].setDisabled(True)
                self.status_colors[idx].setStyleSheet('background-color: black')
                self.radio_btns[idx].setDisabled(True)

            else:
                self.buttons[idx].clicked.connect(self.buttons[idx].btn_clicked)
                self.buttons[idx].status_changed.connect(self.status_colors[idx].status_changed)
                self.buttons[idx].status_changed.connect(self.signal_send_status_changed)
                self.radio_btns[idx].signal_rbtn_checked.connect(self.set_target)

        self.signal_send_target_idx.connect(self.controller.joystick.joystick.set_target_idx)
        print('[CONTROLLER] Initialized')
        self.signal_control_init_chk.emit()
        #self.controller.joystick.start()

    @pyqtSlot()
    def run(self):
        #self.mqtt_client.start()
        self.controller.joystick.start()
