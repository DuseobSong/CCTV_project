import numpy as np
import pandas as pd
import time

import pyqtgraph as pg
from pyqtgraph import PlotWidget
from PyQt5.QtCore import QThread,  pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QTabWidget, QWidget
from PyQt5.QtGui import QFont


class GraphWidget(PlotWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setBackground('w')


class Graph(QThread):
    signal_request_sensor_data = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.tab_widget = QTabWidget(parent)
        self.tab_widget.setGeometry(0, 0, 380, 300)
        self.temp_graph = GraphWidget(parent)
        self.humi_graph = GraphWidget(parent)
        self.illu_graph = GraphWidget(parent)
        self.temp_graph.resize(370, 290)
        self.humi_graph.resize(370, 290)
        self.illu_graph.resize(370, 290)
        self.pen1 = pg.mkPen(color=(255, 0, 0), width=4)
        self.pen2 = pg.mkPen(color=(0, 0, 255), width=4)
        self.tab_widget.addTab(self.temp_graph, 'TEMPERATURE')
        self.tab_widget.addTab(self.humi_graph, 'HUMIDITY')
        self.tab_widget.addTab(self.illu_graph, 'ILLUMINANCE')
        self.data = None

    @pyqtSlot(object)
    def set_data(self, data):
        self.data = data
        if len(data)>0:
            self.update_plot()

    def update_plot(self):
        if self.data is not None:
            print('[PLOT] Start')
            st = time.time()
            date = self.data['date']
            x = self.data['timestamp']
            xtick = self.data['xtick']
            tick_label = self.data['tick_labels']
            temperature = self.data['temperature']
            humidity = self.data['humidity']
            illuminance = self.data['illuminance']

            font_x = QFont()
            font_x.setPointSize(4)
            font_y = QFont()
            font_y.setPointSize(7)

            self.temp_graph.clear()
            self.humi_graph.clear()
            self.illu_graph.clear()
            # temperature
            self.temp_graph.plot(x, temperature, pen=self.pen1, width=2)
            self.temp_graph.setLabel('left', 'Temperature [C]')
            self.temp_graph.setLabel('bottom', date)
            self.temp_graph.showGrid(x=True, y=True)
            self.temp_graph.setXRange(xtick[0], xtick[-1])
            self.temp_graph.setYRange(-10, 50)
            graph_xticks = self.temp_graph.getAxis('bottom')
            graph_yticks = self.temp_graph.getAxis('left')
            graph_xticks.setTextPen('k')
            graph_yticks.setTextPen('k')
            graph_xticks.setTicks([[item for item in zip(xtick, tick_label)]])
            graph_xticks.tickFont = font_x
            graph_yticks.tickFont = font_y

            # Humidity
            self.humi_graph.plot(x, humidity, pen=self.pen2, width=2)
            self.humi_graph.setLabel('left', 'Humidity [%]')
            self.humi_graph.setLabel('bottom', date)
            self.humi_graph.showGrid(x=True, y=True)
            self.humi_graph.setXRange(xtick[0], xtick[-1])
            self.humi_graph.setYRange(0, 100)
            graph_xticks = self.humi_graph.getAxis('bottom')
            graph_yticks = self.humi_graph.getAxis('left')
            graph_xticks.setTextPen('k')
            graph_yticks.setTextPen('k')
            graph_xticks.setTicks([[item for item in zip(xtick, tick_label)]])
            graph_xticks.tickFont = font_x
            graph_yticks.tickFont = font_y

            #illuminance
            self.illu_graph.plot(x, illuminance, pen=self.pen1, width=2)
            self.illu_graph.setLabel('left', 'Illuminance [ ]')
            self.illu_graph.setLabel('bottom', date)
            self.illu_graph.showGrid(x=True, y=True)
            self.illu_graph.setXRange(xtick[0], xtick[-1])
            self.illu_graph.setYRange(0, 1030)
            graph_xticks = self.illu_graph.getAxis('bottom')
            graph_yticks = self.illu_graph.getAxis('left')
            graph_xticks.setTextPen('k')
            graph_yticks.setTextPen('k')
            graph_xticks.setTicks([[item for item in zip(xtick, tick_label)]])
            graph_xticks.tickFont = font_x
            graph_yticks.tickFont = font_y
            ed = time.time()
            print('[PLOT] END', ed-st)