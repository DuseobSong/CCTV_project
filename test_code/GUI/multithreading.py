import cv2
import sys
from PyQt5.QtWidgets import  QWidget, QLabel, QApplication, QFrame, QPushButton
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import imagezmq

class Thread(QThread):
    changePixmap = pyqtSignal(QImage)
    Pause = True
    port = 5555
    def setPort(self, port):
        self.port = port

    def run(self):
        dummy = np.zeros((300, 400, 3), dtype=np.uint8)
        dummy = QImage(dummy.data, 400, 300, 400 * 3, QImage.Format_RGB888)
        self.changePixmap.emit(dummy)
        image_hub = imagezmq.ImageHub(open_port='tcp://*:'+str(self.port))

        while True:
            if self.Pause==False:
                name, image = image_hub.recv_image()
                print(name)
                image_hub.send_reply(b'OK')
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = image.shape
                bytesPerLine = ch * w
                convertToQtFormat = QImage(image.data, w, h, bytesPerLine, QImage.Format_RGB888)
                p = convertToQtFormat.scaled(400, 300, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)
                cv2.waitKey(1)

            else:
                self.changePixmap.emit(dummy)
                cv2.waitKey(1)

    @pyqtSlot(bool)
    def status_changed(self, status):
        self.Pause = status

class Thread2(QThread):
    changePixmap = pyqtSignal(QImage)
    Pause = True
    def run(self):
        dummy = np.zeros((300, 400, 3), dtype=np.uint8)
        dummy = QImage(dummy.data , 400, 300, 400*3, QImage.Format_RGB888)
        self.changePixmap.emit(dummy)

        cap = cv2.VideoCapture(0)
        while True:
            if self.Pause==False:
                ret, frame = cap.read()
                if ret:
                    #print('th2: chk1')
                    # https://stackoverflow.com/a/55468544/6622587
                    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgbImage.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(400, 300, Qt.KeepAspectRatio)
                    self.changePixmap.emit(p)
                else:
                    #print('th2: chk2')
                    self.changePixmap.emit(dummy)
            else:
                #print('th2: chk3')
                self.changePixmap.emit(dummy)

    @pyqtSlot(bool)
    def status_changed(self, status):
        self.Pause = status

class App(QWidget):
    signal_status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 Video test'
        self.left = 100
        self.top = 100
        self.row = 2
        self.col = 2
        self.width = 400 * self.col +10 * (self.col + 1)
        self.height = 300 * self.row + 10 * (self.row + 1) + 60
        self.port_list = [5555, 5556, 5557, 5558, 5559, 5560, 5561, 5562, 5563]
        self.initUI()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(QImage)
    def setImage2(self, image):
        self.label2.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(QImage)
    def setImage3(self, image):
        self.label3.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot(QImage)
    def setImage4(self, image):
        self.label4.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        self.RUNNING = False
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # create a label
        self.label = QLabel('cam1', self)
        self.label.setGeometry(10,10,400,300)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFrameShape(QFrame.Box)

        self.label2 = QLabel('cam2', self)
        self.label2.setGeometry(420, 10, 400, 300)
        self.label2.setAlignment(Qt.AlignCenter)
        self.label2.setFrameShape(QFrame.Box)

        self.label3 = QLabel('cam3', self)
        self.label3.setGeometry(10, 320, 400, 300)
        self.label3.setAlignment(Qt.AlignCenter)
        self.label3.setFrameShape(QFrame.Box)

        self.label4 = QLabel('cam4', self)
        self.label4.setGeometry(420, 320, 400, 300)
        self.label4.setAlignment(Qt.AlignCenter)
        self.label4.setFrameShape(QFrame.Box)

        self.pbt = QPushButton('Connect', self)
        self.pbt.setGeometry(50, 640, 100, 20)

        th1 = Thread(self)
        th2 = Thread(self)
        th3 = Thread(self)
        th4 = Thread2(self)
        th1.setPort(self.port_list[0])
        th2.setPort(self.port_list[1])
        th3.setPort(self.port_list[2])
        th1.changePixmap.connect(self.setImage)
        th2.changePixmap.connect(self.setImage2)
        th3.changePixmap.connect(self.setImage3)
        th4.changePixmap.connect(self.setImage4)
        self.signal_status_changed.connect(th1.status_changed)
        self.signal_status_changed.connect(th2.status_changed)
        self.signal_status_changed.connect(th3.status_changed)
        self.signal_status_changed.connect(th4.status_changed)

        self.pbt.clicked.connect(self.pbt_clicked)
        th1.start()
        th2.start()
        th3.start()
        th4.start()
        self.show()

    def pbt_clicked(self):
        if(self.RUNNING==False):
            self.RUNNING = True
            self.pbt.setText('Stop')
            self.signal_status_changed.emit(False)
        else:
            self.RUNNING = False
            self.pbt.setText('Connect')
            self.signal_status_changed.emit(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())