import sys
from StreamingWidget import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout

'''
Class
1. DisplayWidget
    camera_threads  : [ threads     ]
    camera_displays : [ Displays    ]
    camera_status   : [ bool        ]

2. ControlPanel
    buttons         : [ CamButtons  ]
    status_colors   : [ StatusColor ]
    ctrl_buttons    : [ CtrlButton  ]

3. SensorDataPlot

Connection
1. DisplayWidget
    slot : camera_status_changed(bool status)
    slot : setImage(QImage)

2. CamButton
    signal: clicked()
    signal: status_changed(bool status)

3. StatusColor
    slot : status_changed(bool status)

4. CtrlButton
    signal : clicked()
'''
#camera_info = ['webcam' for i in range(9)]
#camera_info = ['webcam' for _ in range(4)]
camera_info = ['webcam', 'esp32', 'zmq', 'udp']

class GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(10, 10, 1420, 650)
        self.setWindowTitle('Client GUI v1.0')
        self.display_widget = DisplayWidget(camera_info, self)
        self.control_panel = ControlPanel(len(camera_info), self)
        self.sensor_data_plot = SensorDataPlot(self)

        self.display_widget.camera_threads[3].set_host("0.0.0.0")
        print(self.display_widget.camera_threads[3].host, self.display_widget.camera_threads[3].port)
        # connect signals and slots
        for idx in range(len(camera_info)):
            self.control_panel.buttons[idx].clicked.connect(self.control_panel.buttons[idx].btn_clicked)
            self.control_panel.buttons[idx].status_changed.connect(self.control_panel.status_colors[idx].status_changed)
            self.control_panel.buttons[idx].status_changed.connect(self.display_widget.camera_threads[idx].status_changed)

        for idx in range(len(camera_info)):
            self.display_widget.camera_threads[idx].start()

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GUI()
    sys.exit(app.exec_())