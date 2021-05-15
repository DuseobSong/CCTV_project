import sys, cv2, imagezmq, socket, requests, pickle
from io import BytesIO
import numpy as np
from enum import Enum
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QPointF, QPoint, QRectF, QLineF
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter


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

class Joystick(QWidget):
    send_cmd = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super(Joystick, self).__init__(parent)
        self.setMinimumSize(150, 150)
        self.moving_offset=(QPoint(0, 0))
        self.grab_center = False
        self.__max_distance = 70
        self.init_pwm_x = 993
        self.init_pwn_y = 813
        self.cur_pwm_x = self.init_pwm_x
        self.cur_pwm_y = self.init_pwm_y
        self.prev_pwm_x = self.init_pwm_x
        self.prev_pwm_y = self.init_pwm_y

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
        if 22.5 <= angle < 67.5:

            return (Direction.RightUp, distance)
        elif 67.5 <= angle < 112.5:
            return (Direction.up, distance)
        elif 112.5 <= angle < 157.5:
            return (Direction.LeftUp, distance)
        elif 157.5 <= angle < 202.5:
            return (Direction.Left, distance)
        elif 202.5 <= angle < 247.5:
            return (Direction.LeftDown, distance)
        elif 247.5 <= angle < 292.5:
            return (Direction.Down, distance)
        elif 292.5 <= angle < 337.5:
            return (Direction.RigntDown, distance)
        return (Direction.Right, distance)

    def mousePressEvent(self, ev):
        self.grab_center = self._center_ellipse().contains(ev.pos())
        return super().mousePressEvent(ev)

    def mouseReleaseEvent(self, event):
        self.grab_center = False
        self.moving_offset = QPointF(0, 0)
        self.update()

    def mouseMoveEvent(self, event):
        if self.grab_center:
            print("Moving")
            self.moving_offset = self._bound_joystick(event.pos())
            self.update()
        print(self.joystick_direction())

class CameraControl(QThread):
    def __init__(self, parent=None):
        super().__init__()
        self.joystick = Joystick(self)

    def run(self):
        pass

    @pyqtSlot(int, int)
    def send_ctrl_cmd(self, x, y):
        pass

