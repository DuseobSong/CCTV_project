import cv2, imagezmq, socket, requests, pickle
from io import BytesIO
import numpy as np
import time

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage


class Streaming(QThread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, idx):
        super().__init__()
        self.idx = idx
        self.Pause = True
        self.width = 800
        self.height = 600
        self.channel = 3
        dummy = np.zeros((self.width, self.height, self.channel), dtype=np.uint8)
        self.dummy = QImage(dummy.data, self.width, self.height, self.width * self.channel, QImage.Format_RGB888)

    @pyqtSlot(int, bool)
    def status_changed(self, idx, status):
        if self.idx==idx:
            self.Pause = status


class WebCamStreaming(Streaming):
    def run(self):
        self.changePixmap.emit(self.dummy)
        cam_port = 0
        cap = cv2.VideoCapture(cam_port)

        while not cap.isOpened():
            cam_port += 1
            if cam_port == 3:
                cam_port = 0
            cap = cv2.VideoCapture(cam_port)
            time.sleep(1)

        while True:
            if not self.Pause:
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
            if not self.Pause:
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
    #signal_not_connected = pyqtSignal()
    esp_addr = '192.168.10.32'
    stream_url = 'http://' + esp_addr + ':81/stream'

    def set_esp_addr(self, addr):
        self.esp_addr = addr

    def run(self):
        self.changePixmap.emit(self.dummy)
        while True:
            try:
                res = requests.get(self.stream_url, stream=True)
            except:
                self.signal_not_connected.emit()
                time.sleep(2)
                continue
            break

        for chunk in res.iter_content(chunk_size=100000):
            if len(chunk) > 100:
                try:
                    img_data = BytesIO(chunk)
                    cv_img = cv2.imdecode(np.frombuffer(img_data.read(), np.uint8), 1)
                    cv_img = cv2.resize(cv_img, (800, 600), interpolation=cv2.INTER_AREA)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    image = QImage(cv_img.data, 800, 600, 800*3, QImage.Format_RGB888)
                    if not self.Pause:
                        self.changePixmap.emit(image)
                    else:
                        self.changePixmap.emit(self.dummy)
                    cv2.waitKey(1)
                except Exception as e:
                    print(e)
                    continue


class UDPStreaming(Streaming):
    port = 5555
    host = "192.168.10.201"

    def set_port(self, port):
        self.port = port

    def set_host(self, host):
        self.host = host

    def run(self):
        self.changePixmap.emit(self.dummy)
        max_length = 65540
        print('[UDP]', self.host, self.port)
        frame_info = None
        buffer = None
        frame = None

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print('[UDP] Ready')
        s = [b'\xff'*46080 for x in range(20)]

        while True:
            try:
                frame = b''

                data, addr = sock.recvfrom(46081)
                s[data[0]] = data[1:46081]

                if data[0]==19:
                    for i in range(20):
                        frame += s[i]

                    frame = np.fromstring(frame, dtype=np.uint8)
                    frame = frame.reshape(480, 640, 3)
                    if not self.Pause:
                        image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[1] * 3,
                                       QImage.Format_RGB888)
                        self.changePixmap.emit(image)
                    else:
                        self.changePixmap.emit(self.dummy)
            except:
                continue


'''
    def run(self):
        self.changePixmap.emit(self.dummy)
        max_length = 65540
        print('[UDP]', self.host, self.port)
        frame_info = None
        buffer = None
        frame = None

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        print('[UDP] Ready')
        while True:
            data, address = sock.recvfrom(max_length)
            print('[UDP] Data received')
            if len(data) < 100:
                frame_info = pickle.loads(data)
                if frame_info:
                    nums_of_packs = frame_info['packs']
                    print('[UDP]', nums_of_packs)
                    for i in range(nums_of_packs):
                        data, address = sock.recvfrom(max_length)
                        if i==0:
                            buffer = data
                        else:
                            buffer += data
                    frame = np.frombuffer(buffer, dtype=np.uint8)

                    try:
                        frame = frame.reshape(frame.shape[0], 1)
                        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        if frame is not None and type(frame)==np.ndarray:
                            if not self.Pause:
                                image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[1] * 3, QImage.Format_RGB888)
                                self.changePixmap.emit(image)
                            else:
                                self.changePixmap.emit(self.dummy)
                    except:
                        continue
'''