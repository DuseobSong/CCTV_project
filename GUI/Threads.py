import sys, cv2, imagezmq, socket, requests, pickle
from io import BytesIO
import time
import numpy as np
from enum import Enum
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QPointF, QPoint, QRectF, QLineF
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter
import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

# classes for video streaming
class Streaming(QThread):
    changePixmap = pyqtSignal(QImage)
    Pause = True
    width = 800
    height = 600
    channel = 3
    dummy = np.zeros((width, height, channel), dtype=np.uint8)
    dummy = QImage(dummy.data, width, height, width * channel, QImage.Format_RGB888)

    @pyqtSlot(bool)
    def status_changed(self, status):
        self.Pause = status

class WebCamStreaming(Streaming):
    def run(self):
        self.changePixmap.emit(self.dummy)
        cap = cv2.VideoCapture(0)
        while True:
            if self.Pause==False:
                ret, frame = cap.read()
                if ret:
                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = image.shape
                    bytes_per_line = ch*w
                    image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.changePixmap.emit(image)
                else:
                    self.changePixmap.emit(self.dummy)
            else:
                self.changePixmap.emit(self.dummy)

class ZMQStreaming(Streaming):
    port = 5555
    def set_port(self, port):
        self.port = port

    def run(self):
        self.changePixmap.emit(self.dummy)
        image_hub = imagezmq.ImageHub(open_port='tcp://*:' + str(self.port))
        while True:
            if self.Pause==False:
                name, image = image_hub.recv_image()
                image_hub.send_reply(b'OK')
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = image.shape
                bytes_per_line = w * ch
                image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.changePixmap.emit(image)
            else:
                self.changePixmap.emit(self.dummy)

class ESP32Streaming(Streaming):
    esp_addr = '192.168.10.33'
    stream_url = 'http://' + esp_addr + ':81/stream'

    def set_esp_addr(self, addr):
        self.esp_addr = addr

    def run(self):
        self.changePixmap.emit(self.dummy)
        res = requests.get(self.stream_url, stream=True)

        for chunk in res.iter_content(chunk_size=100000):
            if len(chunk) > 100:
                try:
                    img_data = BytesIO(chunk)
                    cv_img = cv2.imdecode(np.frombuffer(img_data.read(), np.uint8), 1)
                    cv_img = cv2.resize(cv_img, (800, 600), interpolation=cv2.INTER_AREA)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    image = QImage(cv_img.data, 800, 600, 800*3, QImage.Format_RGB888)
                    if self.Pause == False:
                        self.changePixmap.emit(image)
                    else:
                        self.changePixmap.emit(self.dummy)
                    cv2.waitKey(1)
                except Exception as e:
                    print(e)
                    continue


class UDPStreaming(Streaming):
    port = 5555
    host = "192.168.10.51"

    def set_port(self, port):
        self.port = port

    def set_host(self, host):
        self.host = host

    def run(self):
        self.changePixmap.emit(self.dummy)
        max_length = 65540

        frame_info = None
        buffer = None
        frame = None

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))

        while True:
            data, address = sock.recvfrom(max_length)
            if len(data) < 100:
                frame_info = pickle.loads(data)
                if frame_info:
                    nums_of_packs = frame_info['packs']
                    for i in range(nums_of_packs):
                        data, address = sock.recvfrom(max_length)
                        if i==0:
                            buffer = data
                        else:
                            buffer += data
                    frame = np.frombuffer(buffer, dtype=np.uint8)
                    frame = frame.reshape(frame.shape[0], 1)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    if frame is not None and type(frame)==np.ndarray:
                        if self.Pause==False:
                            image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[1] * 3, QImage.Format_RGB888)
                            self.changePixmap.emit(image)
                        else:
                            self.changePixmap.emit(self.dummy)

# Joystick - CameraControl
class Direction(Enum):
    Left = 0
    Right = 1
    Up = 2
    Down = 3
    LeftUp = 4
    LeftDown = 5
    RightUp = 6
    RightDown = 7
    Neutral = -1

class Joystick(QWidget):
    send_cmd = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super(Joystick, self).__init__(parent)
        self.setMinimumSize(150, 150)
        self.moving_offset=(QPoint(0, 0))
        self.grab_center = False
        self.__max_distance = 55
        self.init_pwm_x = 993
        self.init_pwn_y = 813
        self.cur_pwm_x = self.init_pwm_x
        self.cur_pwm_y = self.init_pwm_y
        self.prev_pwm_x = self.init_pwm_x
        self.prev_pwm_y = self.init_pwm_y
        self.min_x = 570
        self.max_x = 1410
        self.min_y = 525
        self.max_y = 960
        self.setGeometry(0, 0, 150, 150)
        self.pressed = False

    def paintEvent(self, event):
        painter = QPainter(self)
        bounds = QRectF(-self.__max_distance, -self.__max_distance, self.__max_distance*2, self.__max_distance*2).translated(self._center())
        bounds2 = QRectF(-30, -30, 60, 60).translated(self._center())
        painter.drawEllipse(bounds)
        painter.drawEllipse(bounds2)
        painter.setBrush(Qt.black)
        painter.dwawEllipse(self._center_ellipse())

    def _center_ellipse(self):
        if self.grab_center:
            return QRectF(-20, -20, 40, 40).translated(self.moving_offset)
        return QRectF(-20, -20, 40, 40).translated(self._center())

    def _center(self):
        return QPointF(self.width()/2, self.height()/2)

    def _bound_joystick(self, point):
        limitLine = QLineF(self._center(), point)
        if(limitLine.length() > self.__max_distance):
            limitLine.setLength(self.__max_distance)
        return limitLine.p2()

    def joystick_direction(self):
        if not self.grab_center:
            return 0;
        norm_vector = QLineF(self._center(), self.moving_offset)
        current_distance = norm_vector.length()
        angle = norm_vector.angle()

        distance = min(current_distance / self.__max_distance, 1.0)
        if current_distance > 30:
            if 22.5 <= angle < 67.5:
                self.calc_pwm(1, 1)
                return (Direction.RightUp, distance)
            elif 67.5 <= angle < 112.5:
                self.calc_pwm(0, 1)
                return (Direction.Up, distance)
            elif 112.5 <= angle < 157.5:
                self.calc_pwm(-1, 1)
                return (Direction.LeftUp, distance)
            elif 157.5 <= angle < 202.5:
                self.calc_pwm(-1, 0)
                return (Direction.Left, distance)
            elif 202.5 <= angle < 247.5:
                self.calc_pwm(-1, -1)
                return (Direction.LeftDown, distance)
            elif 247.5 <= angle < 292.5:
                self.calc_pwm(0, -1)
                return (Direction.Down, distance)
            elif 292.5 <= angle < 337.5:
                self.calc_pwm(1, -1)
                return (Direction.RightDown, distance)
            else:
                self.calc_pwm(1, 0)
                return (Direction.Right, distance)
        else:
            return (Direction.Neutral, 0)

    def mousePressEvent(self, ev):
        self.grab_center = self._center_ellipse().contains(ev.pos())
        self.pressed = True
        return super().mousePressEvent(ev)

    def mouseReleaseEvent(self, event):
        self.grab_center = False
        self.moving_offset = QPointF(0, 0)
        self.update()
        self.pressed = False

    def mouseMoveEvent(self, event):
        if self.grab_center:
            #print("Moving")
            self.moving_offset = self._bound_joystick(event.pos())
            self.update()
        #print(self.joystick_direction())

    def calc_pwm(self, xdiff, ydiff):
        if(self.cur_pwm_x + xdiff <= self.min_x):
            new_x = self.min_x
        elif(self.min_x <= self.cur_pwm_x + xdiff <= self.max_x):
            new_x = self.cur_pwm_x + xdiff
        else:
            new_x = self.max_x

        if (self.cur_pwm_y + ydiff <= self.min_y):
            new_y = self.min_y
        elif (self.min_y <= self.cur_pwm_y + ydiff <= self.max_y):
            new_y = self.cur_pwm_y + ydiff
        else:
            new_y = self.max_y

        print(new_x, new_y)
        self.cur_pwm_x = new_x
        self.cur_pwm_y = new_y
        self.send_cmd.emit(new_x, new_y)

class CLIENT(QThread):
    client = mqtt.Client('server')
    broker = '192.168.10.51'
    port = 1883
    #self.client.connect(self.broker, self.port)

    def set_broker(self, broker_ip):
        self.broker = broker_ip

    def set_port(self, port):
        self.port = port

    def run(self):
        self.client.connect(self.broker, self.port)
        self.client.publish('server/info', '[SERVER] connected')
        while True:
            self.client.loop_start()
            self.client.subscribe('esp32_controller/response')

            self.client.loop_stop()

class Control(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.joystick = Joystick(parent)

    def run(self):
        while True:
            if self.joystick.pressed==True:
                self.joystick.joystick_direction()
                time.sleep(0.1)

'''
class DataRetrive(QThread):
    signal_send_dht_data = pyqtSignal(dict)
    signal_sned_ill_data = pyqtSignal(dict)

    HOST = '192.168.10.51'
    USER = 'server'
    PSWD = 'server'
    DB = 'Project'
    CHST = 'uft8mb4'

    connect = pymysql.connect(host=HOST, user=USER, password=PSWD, db=DB, charset=CHST)
    cur = connect.cursor()

    def set_host(self, host):
        self.HOST = host

    def set_user(self, user):
        self.USER = user

    def set_pswd(self, pswd):
        self.PSWD = pswd

    def set_db(self, db):
        self.DB = db

    def run(self):
        query = 'SELECT * FROM sensor_data'
        while True:
            self.cur.excute(query)
            self.connect.commit()
            data = self.cur.fetchall()
            data = pd.DataFrame(data)

            timestamp = None
            temperature = None
            humidity = None
            illuminance = None

            dht_data = {'time'        : timestamp,
                        'temperature' : temperature,
                        'humidity'    : humidity
                        }

            ill_data = {'time'        : time,
                        'illuminance' : illuminance
                        }
            self.signal_send_dht_data(dht_data)
            self.signal_sned_ill_data(ill_data)

            time.sleep(5)
            '''