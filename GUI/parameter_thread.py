import time
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread


class ParameterManagement(QThread):
    # SQL
    signal_send_sql_param = pyqtSignal(object) # required to initialize Database()
    signal_request_camera_info = pyqtSignal() # connect to DATABASE.send_camera_info
    signal_request_sensor_data = pyqtSignal() # connect to DATABASE.send_sensor_data
    signal_camera_info_received = pyqtSignal()

    # Display
    signal_send_camera_info_display = pyqtSignal(object)
    signal_send_display_param = pyqtSignal(object)

    # MQTT + Control
    signal_send_camera_info_mqtt = pyqtSignal(object)
    signal_send_joystick_param = pyqtSignal(object)
    signal_send_control_btn_param = pyqtSignal(object)
    signal_send_camera_info_control = pyqtSignal(object)
    signal_send_control_param = pyqtSignal(object)

    # Graph
    signal_send_sensor_data = pyqtSignal(object)

    # Run
    signal_run = pyqtSignal()

    def __init__(self):
        super().__init__()
        # chk widget initialization
        self.display_initialized = False
        self.controller_initialized = False

        # SQL param
        self.HOST = '192.168.10.51'
        self.USER = 'server'
        self.PSWD = 'server'
        self.DB = 'Project'
        self.CHST = 'utf8'

        # streaming setting - display
        self.camera_info = None
        self.n_camera = None
        self.esp_idx = None
        self.port_on_use = None
        self.subwin_width = 320
        self.subwin_height = 200
        self.win_interval = 10
        self.win_width = 1000
        self.win_height = 640

        # control panel parameter
        self.width = 400
        self.height = 40 + 100 + 20 + 150 + 20
        self.interval_v1 = 10
        self.interval_v2 = 20
        self.interval_v3 = 15
        self.interval_h1 = 5
        self.interval_h2 = 35
        #self.n_camera

        # joystick parameters
        self.grab_center = False
        self.__max_distance = 55
        self.init_pwm_x = 993
        self.init_pwm_y = 813
        self.cur_pwm_x = self.init_pwm_x
        self.cur_pwm_y = self.init_pwm_y
        self.prev_pwm_x = self.init_pwm_x
        self.prev_pwm_y = self.init_pwm_y
        self.min_x = 570
        self.max_x = 1410
        self.min_y = 525
        self.max_y = 960

        # Sensor data
        self.sensor_data = None

        # Transmission chk
        self.camera_info_chk = False
        self.sql_param_chk = False
        self.display_param_chk = False

    @pyqtSlot(object)
    def set_sensor_data(self, sensor_data):
        if sensor_data is not None:
            self.sensor_data = sensor_data
            print('[MANAGER] Sensor data received')
            print(sensor_data)
        else:
            print('[MANAGER] pass')

    @pyqtSlot(object)
    def set_port_on_use(self, port_list):
        self.port_on_use = port_list

    @pyqtSlot()
    def send_camera_info_display(self):
        self.signal_send_camera_info_display.emit(self.camera_info)

    @pyqtSlot()
    def send_camera_info_control(self):
        self.signal_send_camera_info_control.emit(self.camera_info)

    @pyqtSlot()
    def send_camera_info_mqtt(self):
        self.signal_send_camera_info_mqtt.emit(self.port_on_use)

    @pyqtSlot()
    def send_sql_param(self):
        param = {'host': self.HOST,
                 'user': self.USER,
                 'pswd': self.PSWD,
                 'db': self.DB,
                 'chst': self.CHST
                 }
        self.signal_send_sql_param.emit(param)

    @pyqtSlot()
    def sql_param_received(self):
        self.sql_param_chk = True

    @pyqtSlot(object)
    def set_camera_info(self, camera_info):
        self.camera_info = camera_info
        self.set_initial_parameter_setting(camera_info)

    @pyqtSlot()
    def send_display_param(self):
        if not self.camera_info_chk:
            return

        param = {'camera_info': self.camera_info,
                 'n_camera': self.n_camera,
                 'port_on_use': self.port_on_use,
                 'subwin_width': self.subwin_width,
                 'subwin_height': self.subwin_height,
                 'win_interval': self.win_interval,
                 'win_width': self.win_width,
                 'win_height': self.win_height
                 }
        self.signal_send_display_param.emit(param)

        print('[MANAGER] Parameter-set for Display sent')

    @pyqtSlot()
    def display_param_received(self):
        self.display_param_chk = True

    @pyqtSlot()
    def display_init_chk(self):
        self.display_initialized = True
        print('[MANAGER] Display-widget : CHK')

    @pyqtSlot()
    def send_control_panel_param(self):
        if not self.camera_info_chk:
            return

        param = {'camera_info': self.camera_info,
                 'num_camera': self.n_camera,
                 'width': self.width,
                 'height': self.height,
                 'interval_v1': self.interval_v1,
                 'interval_v2': self.interval_v2,
                 'interval_v3': self.interval_v3,
                 'interval_h1': self.interval_h1,
                 'interval_h2': self.interval_h2
                 }
        self.signal_send_control_param.emit(param)

    @pyqtSlot()
    def control_init_chk(self):
        self.controller_initialized = True
        print('[MANAGER] Controller-widget : CHK')

    @pyqtSlot()
    def send_joystick_param(self):
        param = {'grab_center': self.grab_center,
                 '__max_distance': self.__max_distance,
                 'init_pwm_x': self.init_pwm_x,
                 'init_pwm_y': self.init_pwm_y,
                 'cur_pwm_x': self.cur_pwm_x,
                 'cur_pwm_y': self.cur_pwm_y,
                 'prev_pwm_x': self.prev_pwm_x,
                 'prev_pwm_y': self.prev_pwm_y,
                 'min_x': self.min_x,
                 'max_x': self.max_x,
                 'min_y': self.min_y,
                 'max_y': self.max_y,
                 }
        self.signal_send_joystick_param.emit(param)

    @pyqtSlot()
    def send_control_btn_param(self):
        param = {'init_pwm_x': self.init_pwm_x,
                 'init_pwm_y': self.init_pwm_y,
                 'cur_pwm_x': self.cur_pwm_x,
                 'cur_pwm_y': self.cur_pwm_y,
                 'prev_pwm_x': self.prev_pwm_x,
                 'prev_pwm_y': self.prev_pwm_y,
                 'min_x': self.min_x,
                 'max_x': self.max_x,
                 'min_y': self.min_y,
                 'max_y': self.max_y
                 }
        self.signal_send_control_btn_param.emit(param)

    def set_initial_parameter_setting(self, cam_info):
        '''
        [no] [ip_addr] [mode]
        no : int, 1 - 9
        ip_addr: str, '000,000,000,000'
        moded: str, 'ESP'|'WEBCAM'|'ZMQ'|'UDP'
        '''
        cnt_cam = 0
        esp_idx = []
        port_on_use = []
        tmp_port = 5555
        for idx in range(len(cam_info)):
            tmp_info = cam_info.iloc[idx][:]

            if tmp_info['mode'] != 'None':
                cnt_cam += 1
                if tmp_info['mode'] == 'WEBCAM':
                    port_on_use.append(0)

                elif tmp_info['mode'] == 'ESP':
                    esp_idx.append(idx)
                    port_on_use.append(0)

                elif tmp_info['mode'] == 'ZMQ':
                    port_on_use.append(tmp_port)
                    tmp_port += 1

                elif tmp_info['mode'] == 'UDP':
                    port_on_use.append(tmp_port)
                    tmp_port += 1
            else:
                port_on_use.append(None)



        if cnt_cam == 0:
            print('[ERROR] INVALID CAMERA INFORMATION: Please check your databse.')
            exit(-1)
        self.n_camera = cnt_cam
        self.esp_idx = esp_idx
        self.port_on_use = port_on_use
        self.camera_info_chk = True
        self.signal_camera_info_received.emit()

    def send_run_signal(self):
        self.signal_run.emit()

    def run(self):
        # initialize sql-thread
        while not self.sql_param_chk:
            time.sleep(0.1)
            continue
        print('[MANAGER] Transmission chk. (SQL-thread)')
        self.signal_request_camera_info.emit()
        while self.camera_info is None:
            time.sleep(0.3)
        print('[MANAGER] Camera information loaded')

        while (self.display_initialized*self.controller_initialized) == 0:
            print('[MANAGER]', self.display_initialized*self.controller_initialized)
            time.sleep(0.4)

        print('[MANAGER] Send start-signal')
        self.signal_run.emit()

        print('[MANAGER] GUI initialized')
        print('[MANAGER] Running GUI')

        while True:
            self.signal_request_sensor_data.emit()
            time.sleep(5)



