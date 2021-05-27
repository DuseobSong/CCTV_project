import socket
import pymysql
import paho.mqtt.client as mqtt
import imagezmq
import cv2
import time

def get_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("pwnbit.kr", 443))
    return sock.getsockname()[0]

def on_message(client, userdata, msg):
    print(f"Received '{msg.payload.decode()}' from '{msg.topic}'")
    topic = msg.topic
    global zmq_port
    global server_ip
    zmq_port, server_ip  = msg.payload.decode().split(', ')
    print('Port assigned: ', zmq_port)

cam_no = 4
server_ip = None
zmq_port = None
camera_ip = get_ip()
im_size = (400, 300)
broker_ip = '192.168.10.51'
mqtt_port = 1883 

# MySQL Database - update camera information
connect = pymysql.connect(host=broker_ip, user='camera', password='camera', db='Project', charset='utf8')
cur = connect.cursor()
sql = "UPDATE camera_info set ip_addr='{}', mode='ZMQ' where no={}".format(camera_ip, cam_no)
cur.execute(sql)
connect.commit()
connect.close()

# request port to server
MQTT = mqtt.Client('camera_'+str(cam_no))
MQTT.connect(broker_ip, mqtt_port)
MQTT.on_message = on_message
MQTT.subscribe('server/camera/{}/port'.format(cam_no))

while zmq_port is None:
    MQTT.loop_start()
    MQTT.publish('camera/{}/port_request'.format(cam_no), str(camera_ip))
    print('camera/{}/port_request, {}'.format(cam_no, camera_ip))
    time.sleep(0.5)
MQTT.loop_stop()

# send request
sender = imagezmq.ImageSender(connect_to='tcp://'+server_ip+':'+str(zmq_port))
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    try:
        if ret == True:
            frame = cv2.resize(frame, im_size)
            cv2.waitKey(1)
            sender.send_image('camera_'+str(cam_no), frame)
            if(cv2.waitKey(10) == ord('q')):
                break
    except:
        continue

cap.release()



