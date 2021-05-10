import socket
import imagezmq
import requests
import numpy as np
import time
import cv2
from io import BytesIO

sender = imagezmq.ImageSender(connect_to='tcp://192.168.10.201:5557')
server_name = socket.gethostname()

ip_addr = '192.168.10.33'
stream_url = 'http://' + ip_addr + ':81/stream'

res = requests.get(stream_url, stream=True)

for chunk in res.iter_content(chunk_size=100000):
    if len(chunk) > 100:
        try:
            start_time = time.time()
            img_data = BytesIO(chunk)
            cv_img = cv2.imdecode(np.frombuffer(img_data.read(), np.uint8), 1)
            cv_resized_img = cv2.resize(cv_img, (800, 600), interpolation=cv2.INTER_AREA)
            elapsed_ms = (time.time() - start_time) * 1000
            cv2.waitKey(1)
            sender.send_image(server_name, cv_resized_img)
            cv2.waitKey(10)
            print(f'elapsed_ms : {elapsed_ms}')
        except Exception as e:
            print(e)
            continue
