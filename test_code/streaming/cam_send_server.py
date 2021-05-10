import socket
import imagezmq
import requests
import numpy as np
import cv2

sender = imagezmq.ImageSender(connect_to='tcp://192.168.10.201:5555')
server_name = 'work01'

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if ret == True:
        frame = cv2.resize(frame, (400, 300))
        cv2.waitKey(1)
        sender.send_image(server_name, frame) 
        if(cv2.waitKey(10) == ord('q')):
            break;
cap.release()
