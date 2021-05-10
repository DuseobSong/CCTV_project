import sys, cv2, imagezmq, socket, requests, pickle
from io import BytesIO
import numpy as np
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap


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

