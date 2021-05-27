from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget
from graph_thread import *


class TabWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setGeometry(1020, 340, 380, 300)
        self.graph_thread = Graph(self)
        self.camera_info = None
        print('[GRAPH] Initialized')

    @pyqtSlot()
    def run(self):
        self.graph_thread.start()
