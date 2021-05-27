import paho.mqtt.client as mqtt
from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal
import time
import socket

class CLIENT(QThread):
    signal_send_test_msg = pyqtSignal()
    signal_request_camera_info = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.client = mqtt.Client('server')
        self.host_ip = None
        self.broker = '192.168.10.51'
        self.port = 1883
        self.port_on_use = None
        self.esp_idx = None
        self.get_server_ip()

    def get_server_ip(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('pwnbit.kr', 443))
        self.host_ip = sock.getsockname()[0]

    def set_broker(self, broker_ip):
        self.broker = broker_ip

    def set_port(self, port):
        self.port = port

    def on_message(self, client, userdata, msg):
        print(f"Received '{msg.payload.decode()}' from '{msg.topic}' topic")
        topic = msg.topic
        payload = msg.payload.decode() # ip address
        type, idx, content = topic.split('/')
        # topic : camera/[idx]/request_port
        #print(self.port_on_use)
        #print('[MQTT]',type, int(idx), content)
        print('[MQTT] server/camera/{}/port'.format(idx), str(self.port_on_use[int(idx)-1]))
        self.client.publish('server/camera/{}/port'.format(idx), str(self.port_on_use[int(idx)-1])+', '+self.host_ip)

    @pyqtSlot(object)
    def set_camera_info(self, port_on_use):
        self.port_on_use = port_on_use
        print('[MQTT] Camera information loaded')

    @pyqtSlot()
    def recv_test_signal(self):
        print('[MQTT] Test msg received')
        time.sleep(1)
        self.signal_send_test_msg.emit()

    @pyqtSlot(int, int, int)
    def msg_publish(self, target_idx, new_x, new_y):
        topic = 'server/esp32_controller_{}/cmd'.format(target_idx)
        command = "{'x': %d, 'y': %d}"%(new_x, new_y)
        print('[MQTT]: ', topic, command)
        self.client.publish(topic, command)

    def run(self):
        self.get_server_ip()
        time.sleep(0.4)
        print('[MQTT] Request camera information')
        while self.port_on_use is None:
            self.signal_request_camera_info.emit()
            time.sleep(0.3)

        print('[MQTT] Start.')
        self.client.connect(self.broker, self.port)
        self.client.publish('server/info', '[SERVER] connected')
        self.client.on_message = self.on_message

        for idx in range(9):
            self.client.subscribe('esp32_controller_{}/response'.format(idx+1))
            self.client.subscribe('camera/{}/port_request'.format(idx+1))

        while True:
            self.client.loop_forever()
