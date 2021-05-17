import sys, numpy as np
from Threads import *
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QFrame, QPushButton, QTabWidget
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
'''
=== camera_info ===
dictionary:
    {'source': ['webcam' | 'esp32']}

'''
class Display(QLabel):
    def __init__(self, width ,height, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        dummy = np.zeros((self.width, self.height, 3), dtype=np.uint8)
        self.dummy = QImage(dummy.data, self.width, self.height, self.width*3, QImage.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(self.dummy))
        self.setFrameShape(QFrame.Box)
        self.setAlignment(Qt.AlignCenter)

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.setPixmap(QPixmap.fromImage(image).scaled(self.width, self.height, Qt.KeepAspectRatio))

class DisplayWidget(QFrame):
    def __init__(self, camera_info, parent=None):
        super().__init__(parent)
        self.camera_info = camera_info
        self.camera_threads = []
        self.camera_displays = []
        self.camera_ports = [port for port in range(5555, 5565)]
        self.camera_status = []
        self.num_camera = 1
        self.subwin_width = 320
        self.subwin_height = 200
        self.win_interval = 10
        self.win_width = 1000
        self.win_height = 640
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setGeometry(5, 5, self.win_width, self.win_height)

        self.chk_variable()
        self.set_cam_no()
        self.set_display()

    def chk_variable(self):
        if isinstance(self.camera_info, list)==False:
            print('[ERROR] INVALID CAMERA INFO')
            exit(-1)

    def set_cam_no(self):
        no_input = len(self.camera_info)
        if no_input < 1:
            print('[ERROR] No Camera input.')
            exit(-1)
        elif no_input==1:
            self.num_camera = 1
            self.subwin_width = self.subwin_width * 3 + self.win_interval * 2
            self.subwin_height = self.subwin_height * 3 + self.win_interval * 2
            self.win_interval = 0
        elif no_input <=4 :
            self.num_camera = 4
            self.subwin_width = int(self.subwin_width*3/2)
            self.subwin_height = int(self.subwin_height*3/2)
            self.win_interval = 20
        elif no_input <= 9:
            self.num_camera = 9
            self.win_interval = 10
        else:
            print("[ERROR] Number of cameras must be less than 9.")
            exit(-1)

    def set_display(self):
        disp_per_line = int(np.sqrt(self.num_camera))
        port_idx = 0

        for idx in range(len(self.camera_info)):
            self.camera_displays.append(Display(self.subwin_width, self.subwin_height, self))
            self.camera_displays[idx].move(10 + (self.subwin_width + self.win_interval) * (idx%disp_per_line),
                                                  10 + (self.subwin_height + self.win_interval) * (idx//disp_per_line))#,
                                                  #self.subwin_width,
                                                  #self.subwin_height)
            self.camera_status.append(False)

            if self.camera_info[idx] == 'webcam':
                self.camera_threads.append(WebCamStreaming(self))

            elif self.camera_info[idx] == 'esp32':
                self.camera_threads.append(ESP32Streaming(self))

            elif self.camera_info[idx] == 'zmq':
                self.camera_threads.append(ZMQStreaming(self))
                self.camera_threads[idx].set_port(self.camera_ports[port_idx])
                print(self.camera_ports[port_idx])
                port_idx += 1

            elif self.camera_info[idx] == 'udp':
                self.camera_threads.append(UDPStreaming(self))
                self.camera_threads[idx].set_port(self.camera_ports[port_idx])
                print(self.camera_ports[port_idx])
                port_idx += 1
                # required to set ip address

            else:
                print('[ERROR] INVALID VIDEO SOURCE')
                exit(-1)

            self.camera_threads[idx].changePixmap.connect(self.camera_displays[idx].setImage)

    @pyqtSlot(int, bool)
    def camera_status_changed(self, no, status):
        if(no < 0 or no > self.num_camera-1):
            print('[ERROR] INVALID CAMERA NUMBER')
            return
        self.camera_status[no] = status

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
        if(self.RUNNING == False):
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
        if self.status==True:
            self.setStyleSheet('background-color: red')
        else:
            self.setStyleSheet('background-color: green')

class CtrlButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 50
        self.height = 50

class CameraControl(QWidget):
    signal_send_cmd = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.joystick = Control(self)
        self.client = CLIENT()
        self.joystick.joystick.send_cmd.connect(self.pub_msg)
        self.client.start()
        self.setGeometry(115, 160, 150, 150)
        self.joystick.start()

    @pyqtSlot(int, int)
    def pub_msg(self, x, y):
        self.client.client.publish('server/cmd',
                                   "{'x': %d, 'y':%d}"%(x, y))

class ControlPanel(QFrame):
    def __init__(self, num_camera, parent=None):
        super().__init__(parent)
        self.width = 400
        self.height = 40 + 100 + 20 + 150 + 20
        self.interval_v1 = 10
        self.interval_v2 = 20
        self.interval_v3 = 15
        self.interval_h1 = 10
        self.interval_h2 = 20
        self.num_camera = num_camera
        self.setGeometry(1010, 5, self.width, self.height)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.buttons = [CamButton(self) for _ in range(9)]
        self.status_colors = [StatusColor(self) for _ in range(9)]

        self.joystick_usage = True
        if self.joystick_usage == False:
            self.ctrl_btns = [CtrlButton(self) for _ in range(4)]
        else:
            self.joystick = CameraControl(self)
            self.joystick.show()
        self.setButtons()

    def setButtons(self):
        # camera buttons
        for idx in range(9):
            width1 = self.buttons[idx].width
            height1 = self.buttons[idx].height
            width2 = self.status_colors[idx].width
            height2 = self.status_colors[idx].height
            x1 = self.interval_h1 + (width1 + self.interval_h1 + width2 + self.interval_h2) * (idx %3)
            x2 = self.interval_h1 + width1 + self.interval_h1 + (width2 + self.interval_h2 + width1 + self.interval_h1) * (idx % 3)
            y1 = 40 + self.interval_v1 + (height1 + self.interval_v1) * (idx // 3)
            y2 = 40 + self.interval_v3 + (height2 + self.interval_v2) * (idx // 3)

            self.buttons[idx].setGeometry(x1, y1, width1, height1)
            self.buttons[idx].no = idx+1
            self.buttons[idx].setText('Cam '+str(idx+1)+' : Off')
            self.status_colors[idx].setGeometry(x2, y2, width2, height2)

        for idx in range(self.num_camera, 9):
            self.buttons[idx].setDisabled(True)
            self.status_colors[idx].setStyleSheet('background-color: black')

        # Camera control buttons
        self.ctrl_btns[0].setGeometry(115 + 50, 40 + 100 + 20, 50, 50) # up
        self.ctrl_btns[0].setText('Up')
        self.ctrl_btns[1].setGeometry(115 + 50, 40 + 100 + 20 + 100, 50, 50) # down
        self.ctrl_btns[1].setText('Down')
        self.ctrl_btns[2].setGeometry(115, 40 + 100 + 20 + 50, 50, 50) # left
        self.ctrl_btns[2].setText('Left')
        self.ctrl_btns[3].setGeometry(115 + 100, 40 + 100 + 20 + 50, 50, 50) # right
        self.ctrl_btns[3].setText('Right')

'''
Sensor data visualization

'''
class SensorDataPlot(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(1020, 340, 380, 300)
        self.dht11 = QWidget()
        self.dht_label = QLabel(self.dht11)
        self.dht_label.setGeometry(5, 5, 200, 20)
        self.dht_label.setText('Temperature & Humidity')
        self.DHT_GRAPH = QLabel(self.dht11)
        self.DHT_GRAPH.setGeometry(5, 35, 360, 220)
        self.DHT_GRAPH.setFrameShape(QFrame.Box)
        self.DHT_GRAPH.setAlignment(Qt.AlignCenter)
        self.addTab(self.dht11, 'DHT11')

        self.ill = QWidget()
        self.ill_label = QLabel(self.ill)
        self.ill_label.setGeometry(5, 5, 100, 20)
        self.ill_label.setText('Illuminance')
        self.ILL_GRAPH = QLabel(self.ill)
        self.ILL_GRAPH.setGeometry(5, 35, 360, 220)
        self.ILL_GRAPH.setFrameShape(QFrame.Box)
        self.ILL_GRAPH.setAlignment(Qt.AlignCenter)
        self.addTab(self.ill, 'Illuminance')

    def query_data(self):
        pass

    def plot_data(self):
        pass