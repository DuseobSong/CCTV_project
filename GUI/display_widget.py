import numpy as np
import pandas as pd
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
from PyQt5.QtWidgets import QLabel, QFrame, QWidget
from PyQt5.QtGui import QImage, QPixmap

from streaming_thread import *


class Display(QLabel):
    def __init__(self, width, height, parent=None):
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
    def set_image(self, image):
        self.setPixmap(QPixmap.fromImage(image).scaled(self.width, self.height, Qt.KeepAspectRatio))


class InitParam(QThread):
    signal_request_display_param = pyqtSignal()
    signal_resend_display_param = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.received = False

    def resend_param(self, param):
        self.signal_resend_param.emit(param)

    @pyqtSlot(object)
    def on_receive(self, param):
        print('[DISPLAY-init] Parmaeter-set received')
        self.received = True
        self.signal_resend_display_param.emit(param)

    def run(self):
        while not self.received:
            self.signal_request_display_param.emit()
            time.sleep(1)



class DisplayWidget(QFrame):
    signal_display_param_chk = pyqtSignal()
    signal_status_changed = pyqtSignal(int, bool)
    signal_display_init_chk = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_info = None
        self.camera_ports = None
        self.camera_threads = []
        self.camera_displays = []
        self.camera_status = []
        self.display_slots = []

        self.num_camera = None
        self.num_windows = None
        self.subwin_width = None
        self.subwin_height = None
        self.win_interval = None
        self.win_width = None
        self.win_height = None

        self.param_loaded = False
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.initializer = InitParam(self)
        self.initializer.signal_resend_display_param.connect(self.set_param)

    @pyqtSlot(object)
    def set_param(self, param):
        self.camera_info = param['camera_info']
        self.num_camera = param['n_camera']
        self.camera_ports = param['port_on_use']
        self.subwin_width = param['subwin_width']
        self.subwin_height = param['subwin_height']
        self.win_interval = param['win_interval']
        self.win_width = param['win_width']
        self.win_height = param['win_height']
        print('[DISPLAY] Parameter-set received')
        self.initializer.working=False
        self.initializer.quit()
        time.sleep(0.2)
        self.setGeometry(5, 5, self.win_width, self.win_height)
        self.set_cam_no()
        self.set_display()
        #self.run_threads()

    @pyqtSlot(int, bool)
    def camera_status_changed(self, no, status):
        if no < 0 or no > self.num_camera - 1:
            print('[ERROR] INVALID CAMERA NUMBER')
            return
        self.camera_status[no] = status
        self.signal_status_changed.emit(no, status)

    @pyqtSlot()
    def run_threads(self):
        for idx in range(self.num_camera):
            self.camera_threads[idx].start()

    def set_cam_no(self):
        no_input = self.num_camera
        if no_input < 1:
            print('[ERROR] No Camera input.')
            exit(-1)
        elif no_input==1:
            self.num_windows = 1
            self.subwin_width = self.subwin_width * 3 + self.win_interval * 2
            self.subwin_height = self.subwin_height * 3 + self.win_interval * 2
            self.win_interval = 0
        elif no_input <=4 :
            self.num_windows = 4
            self.subwin_width = int(self.subwin_width*3/2)
            self.subwin_height = int(self.subwin_height*3/2)
            self.win_interval = 20
        elif no_input <= 9:
            self.num_windows = 9
            self.win_interval = 10
        else:
            print("[ERROR] Number of cameras must be less than 9.")
            exit(-1)

    def set_display(self):
        disp_per_line = int(np.sqrt(self.num_windows))
        dummy = np.zeros((self.subwin_width, self.subwin_height, 3), dtype=np.uint8)
        self.dummy = QImage(dummy.data, self.subwin_width, self.subwin_height, self.subwin_width * 3, QImage.Format_RGB888)

        for idx in range(self.num_windows):
            self.camera_displays.append(Display(self.subwin_width, self.subwin_height, self))
            self.camera_displays[idx].move(10 + (self.subwin_width + self.win_interval) * (idx % disp_per_line), 10 + (self.subwin_height + self.win_interval) * (idx // disp_per_line))
            self.camera_status.append(False)

            ip_addr = self.camera_info['ip_addr'].iloc[idx]
            tmp_mode = self.camera_info['mode'].iloc[idx]

            if tmp_mode == 'WEBCAM':
                self.camera_threads.append(WebCamStreaming(idx))
                self.camera_threads[idx].changePixmap.connect(self.camera_displays[idx].set_image)
                self.signal_status_changed.connect(self.camera_threads[idx].status_changed)

            elif tmp_mode == 'ESP':
                self.camera_threads.append(ESP32Streaming(idx))
                self.camera_threads[idx].set_esp_addr(ip_addr)
                self.camera_threads[idx].changePixmap.connect(self.camera_displays[idx].set_image)
                self.signal_status_changed.connect(self.camera_threads[idx].status_changed)

            elif tmp_mode == 'ZMQ':
                self.camera_threads.append(ZMQStreaming(idx))
                #self.camera_threads[idx].set_host(ip_addr) # ip address : server ip
                self.camera_threads[idx].set_port(self.camera_ports[idx])
                self.camera_threads[idx].changePixmap.connect(self.camera_displays[idx].set_image)
                self.signal_status_changed.connect(self.camera_threads[idx].status_changed)

            elif tmp_mode == 'UDP':
                self.camera_threads.append(UDPStreaming(idx))
                #self.camera_threads[idx].set_host(ip_addr)
                self.camera_threads[idx].set_port(self.camera_ports[idx])
                self.camera_threads[idx].changePixmap.connect(self.camera_displays[idx].set_image)
                self.signal_status_changed.connect(self.camera_threads[idx].status_changed)

            else:
                print('[ERROR] INVALID VIDEO SOURCE')

            self.camera_displays[idx].show()
        self.signal_display_init_chk.emit()
        print('[DISPLAY] Initialized')
