import paho.mqtt.client as mqtt

class CLIENT():
    def __init__(self, server, path, port):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(server, port, 60)
        self.path = path
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        print('Connected');
        self.client.subscribe(self.path)

    def on_message(self, client, userdata, msg):
        print(msg.topic + ' ' +str(msg.payload))

#client_new = CLIENT(server='127.0.0.1', path='#', port=1883)
client_new = CLIENT(server='192.168.10.201', path='#', port=1883)