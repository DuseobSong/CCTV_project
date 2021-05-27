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

1. sql - 카메라 정보 로딩
2. mqtt - 카메라 정보 요청 -> 카메라 정보 로딩

'''
import sys
from parameter_thread import *
from display_widget import *
from graph_widget import *
from control_widget import *
from sql_thread import *
from mqtt_thread import *

from PyQt5.QtWidgets import QWidget, QApplication


class GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.camera_info = None
        self.setGeometry(10, 10, 1420, 650)
        self.setWindowTitle('Client GUI v1.0')
        # initialize threads
        self.param_thread = ParameterManagement()
        self.sql_thread = Database()
        self.mqtt_client = CLIENT()

        # define widgets
        self.display_widget = DisplayWidget(self)
        self.control_widget = ControlPanel(self)
        self.tab_widget = TabWidget(self)

        # Linking signals and slots
        self.sql_thread.signal_request_sql_param.connect(self.param_thread.send_sql_param)
        self.param_thread.signal_send_sql_param.connect(self.sql_thread.set_param)
        self.sql_thread.signal_sql_param_received.connect(self.param_thread.sql_param_received) # Transmission chk
        self.sql_thread.signal_send_camera_info.connect(self.param_thread.set_camera_info)
        self.param_thread.signal_camera_info_received.connect(self.sql_thread.camera_info_chk)  # Transmission chk

        self.param_thread.signal_request_sensor_data.connect(self.sql_thread.send_sensor_data)
        self.sql_thread.signal_send_sensor_data.connect(self.param_thread.set_sensor_data) # SQL - Done

        self.display_widget.initializer.signal_request_display_param.connect(self.param_thread.send_display_param)
        self.param_thread.signal_send_display_param.connect(self.display_widget.initializer.on_receive)
        self.display_widget.signal_display_init_chk.connect(self.param_thread.display_init_chk) # chk initialized

        self.control_widget.initializer.signal_request_panel_param.connect(self.param_thread.send_control_panel_param)
        self.param_thread.signal_send_control_param.connect(self.control_widget.initializer.resend_panel_param)
        self.control_widget.signal_control_init_chk.connect(self.param_thread.control_init_chk) # chk initialized

        self.tab_widget.graph_thread.signal_request_sensor_data.connect(self.sql_thread.send_sensor_data)
        self.sql_thread.signal_send_sensor_data.connect(self.tab_widget.graph_thread.set_data)
        self.control_widget.controller.joystick.joystick.send_cmd.connect(self.mqtt_client.msg_publish)

        self.control_widget.controller.joystick.joystick.signal_request_joystick_param.connect(self.param_thread.send_joystick_param)
        self.param_thread.signal_send_joystick_param.connect(self.control_widget.controller.joystick.joystick.set_param)
        self.control_widget.controller.joystick.joystick.signal_send_test_msg.connect(self.mqtt_client.recv_test_signal)
        self.mqtt_client.signal_send_test_msg.connect(self.control_widget.controller.joystick.joystick.test_msg_received)

        self.mqtt_client.signal_request_camera_info.connect(self.param_thread.send_camera_info_mqtt)
        self.param_thread.signal_send_camera_info_mqtt.connect(self.mqtt_client.set_camera_info)

        self.param_thread.signal_run.connect(self.display_widget.run_threads)
        self.param_thread.signal_run.connect(self.control_widget.run)
        self.param_thread.signal_run.connect(self.tab_widget.run)
        self.param_thread.signal_run.connect(self.mqtt_client.start)

        # Start background threads
        self.param_thread.start() # chk always run, managing widget parameters, camera info, sensor data
        time.sleep(0.1)
        self.sql_thread.start() #chk always run
        time.sleep(0.3)

        # Layout initialization
        self.display_widget.initializer.start()
        self.control_widget.initializer.start()
        self.control_widget.signal_send_status_changed.connect(self.display_widget.camera_status_changed)

        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GUI()
    sys.exit(app.exec_())