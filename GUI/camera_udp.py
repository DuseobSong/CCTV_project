import cv2
import socket
import math
import pickle
import pymysql
import time
import paho.mqtt.client as mqtt

def get_ip():
    tmp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tmp_sock.connect(('pwnbit.kr', 443))
    return tmp_sock.getsockname()[0]

def on_message(client, userdata, msg):
    print(f"Received '{msg.payload.decode()}' from '{msg.topic}'")
    topic = msg.topic
    global udp_port
    global server_ip

    udp_port, server_ip = msg.payload.decode().split(', ')
    print(udp_port, server_ip)

max_length = 65000
cam_no = 3
server_ip = None
udp_port = None
camera_ip = get_ip()
im_size = (400, 300)
broker_ip = '192.168.10.51'
mqtt_port = 1883

# MySQL Database - update camera information
connect = pymysql.connect(host=broker_ip, user='camera', password='camera', db='Project', charset='utf8')
cur = connect.cursor()
sql = "UPDATE camera_info set ip_addr='{}', mode='UDP' where no={}".format(camera_ip, cam_no)
cur.execute(sql)
connect.commit()
connect.close()

# request port to server
MQTT = mqtt.Client('camera'+str(cam_no))
MQTT.connect(broker_ip, mqtt_port)
MQTT.on_message = on_message
MQTT.subscribe('server/camera/{}/port'.format(cam_no))

while udp_port is None:
    MQTT.loop_start()
    MQTT.publish('camera/{}/port_request'.format(cam_no), str(camera_ip))
    print('camera/{}/port_request'.format(cam_no), str(camera_ip))
    time.sleep(0.5)
MQTT.loop_stop()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (640, 480))
        d = frame.flatten()
        s = d.tostring()
        for i in range(20):
            sock.sendto(bytes([i]) + s[i*46080:(i+1)*46080], (server_ip, int(udp_port)))
            cv2.waitKey(1)
    else:
        continue

