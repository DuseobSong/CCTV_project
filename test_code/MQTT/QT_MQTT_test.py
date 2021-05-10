import sys
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QFrame, QPushButton
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import cv2

class ImgThread(QThread):
    Pause = True

    def run(self):
        dummy = np.zeros((300, 400, 4), dtype=np.uint8)
        dummy = QImage(dummy.data, 400, 300, 400*3, QImage)

class CtrlThread(QThread):
    def run(self):