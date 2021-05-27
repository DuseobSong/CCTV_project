/*
 * Microcontroller : ESP32
 * Sensors         : DHT11, Illuminance sensor   
 * Controller      : 2 Servo motors with PCA9685 - I2C communicationnn
 * 
 * Sensor data will be uploaded every 10 seconds. [MySQL]
 * Servo motor control command will be delivered through MQTT communication
 * 
 * Messages
 * 1. Sensor
 *  - esp32_sensor/msg          [ESP32_SENSOR]
 *  
 * 2. Controller
 * 
 *  - esp32_controller/msg      [ESP32_CONTROLLER]
 *  - esp32_controller/response [ESP32_CONTROLLER]
 *  - server/cmd                [SERVER]
 *  - server/response           [SERVER]
 */

#include "DHTesp.h"
#include <ArduinoJson.h>
#include <WiFi.h>
#include <Wire.h>
#include <MySQL_Connection.h>
#include <MySQL_Cursor.h>
#include <PubSubClient.h>
#include <Adafruit_PWMServoDriver.h>

// Sensor pins
#define ILLPIN 32
#define DHTPIN 33 
#define DHTTYPE DHT11

// Servo motor setup
#define RESOLUTION_VAL 3
#define initX 331 * RESOLUTION_VAL
#define initY 271 * RESOLUTION_VAL
#define frequency 50 * RESOLUTION_VAL
#define X_MIN 190 * RESOLUTION_VAL // 570
#define X_MAX 470 * RESOLUTION_VAL // 1410
#define Y_MIN 175 * RESOLUTION_VAL // 525
#define Y_MAX 320 * RESOLUTION_VAL // 960

// Sensors
DHTesp dht;

// Network Connection
const char* ssid = "YIIT_DEV2G";
const char* pswd = "0535551333";
const char* mqtt_server = "192.168.10.51";
const int mqtt_port = 1883;
const int cam_no = 1;
WiFiClient mqttClient;
PubSubClient mqtt_client(mqttClient);

// Database connnection
char user[] = "sensor";
char pswdSQL[] = "sensor";

WiFiClient sqlClient;
IPAddress sql_server_addr(192, 168, 10, 51);
WiFiServer server(80);
MySQL_Connection conn((Client *)&sqlClient);

// Sensors
static float temperature = 0.1; // default
static float humidity = 0.1;    // default

// PWM driver
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

static int cur_x, cur_y;
static int target_x, target_y;

// Multithread tasks
static void recvMsg(void *param); // PWM control message
static void sendData(void *param); // Sensor data

void connection_init() {
  WiFi.begin(ssid, pswd);
  Serial.print("[WiFi] Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.println("[WiFi] Connected.");

  mqtt_client.setServer(mqtt_server, mqtt_port);
  mqtt_client.setCallback(callback);

  String cam_ip = WiFi.localIP().toString();
  String SQL = String("update Project.camera_info set ip_addr='") + cam_ip + String("' where no=1;");
  Serial.print("[SQL]: ");
  Serial.println(SQL);
  char SQL_[255];
  SQL.toCharArray(SQL_, SQL.length());
  while(true){
    if(conn.connect(sql_server_addr, 3306, "controller", "controller")){
      Serial.println("[ESP32_CONTROLLER_1] DB Connected.");
      break;
    }else{
      Serial.println("[ESP32_CONTROLLER_1] DB Connection failed. Retry in a few seconds.");
      delay(200);
      continue;
    }
    MySQL_Cursor *cur_mem = new MySQL_Cursor(&conn);
    cur_mem->execute(SQL_);
    delete cur_mem;
    Serial.println("[ESP32_CONTROLLER_1] IP address updated.");
  }
}

// SEND SENSOR DATA
void getDHTdata(void) {
  delay(dht.getMinimumSamplingPeriod());
  humidity = dht.getHumidity();
  temperature = dht.getTemperature();
}

int getIlluminance(void) {
  return analogRead(ILLPIN);
}

static void sendData(void *param) {

  char INSERT_SQL[255];

  while(true){
  
      getDHTdata();
      sprintf(INSERT_SQL, "insert into Project.sensor_data(no, controller_no, date, time, temperature, humidity, illuminance) values (%d, %d, curdate(), curtime(), %f, %f, %d)", 0, 1, temperature, humidity, getIlluminance());
  
      MySQL_Connection conn((Client *)&sqlClient);
      if (conn.connect(sql_server_addr, 3306, user, pswdSQL)) {
        //delay(500);
        Serial.println("[SQL] DB connected");
      } else {
        Serial.println("[SQL] Connection failed. Recording data.");
        continue;
      }
  
      MySQL_Cursor *cur_mem = new MySQL_Cursor(&conn);
      cur_mem->execute(INSERT_SQL);
  
      delete cur_mem;
      Serial.println("[SQL] Closing connection\n");
      mqtt_client.publish("esp32_sensor_1/msg", "[ESP32_SENSOR_1] Sensor data updated.");
      delay(10*1000);
  }
  vTaskDelete(NULL);
}

// RECV COMMAND -- Servo motor control
void pwm_setup(){
  cur_x = initX;
  cur_y = initY;
  target_x = initX;
  target_y = initY;

  pwm.begin();
  pwm.setPWMFreq(frequency);
  pwm.setPWM(0, 0, cur_x);
  pwm.setPWM(1, 0, cur_y);
}

void reconnect(){
  while(!mqtt_client.connected()){
    Serial.print("[MQTT] Connecting to MQTT-broker...");
    if(mqtt_client.connect("ESP32_controller_1")){
      Serial.println("[MQTT] Connected");
      mqtt_client.publish("esp32_controller_1/msg", "[ESP32_CONTROLLER_1]connected");
      mqtt_client.subscribe("server/esp32_controller_1/cmd");
      mqtt_client.subscribe("server/response");
    }else{
      Serial.print("[MQTT] Connetion failed, rc = ");
      Serial.print(mqtt_client.state());
      Serial.println(" try again in a few seconds");
      delay(200);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length){
  Serial.println("[Client] Message received");
  Serial.print("Topic: ");
  Serial.println(topic);
  for(int i=0; i<length; i++){
    Serial.print((char)payload[i]);
  }
  Serial.println();
  Serial.println("-------------------------------------");

  StaticJsonBuffer<200> json_buffer;
  JsonObject& parsed = json_buffer.parseObject(payload);
  if(!parsed.success()){
    Serial.println("[MQTT] MSG parsing failed.");
    mqtt_client.publish("esp32_controller_1/response", "[ESP32_CONTROLLER_1] Parsing failed.");
    return;
  }
  //int idx = parsed["idx"];
  int recv_x = parsed["x"];
  int recv_y = parsed["y"];
  
  if(recv_x <= X_MIN){
    target_x = X_MIN;
  }else if(recv_x >= X_MAX){
    target_x = X_MAX;
  }else{
    target_x = recv_x;
  }
  
  if(recv_y <= Y_MIN){
    target_y = Y_MIN;
  }else if(recv_y >= Y_MAX){
    target_y = Y_MAX;
  }else{
    target_y = recv_y;
  }
  
  Serial.print("[recv_x, recv_y, target_x, target_y] : ");
  Serial.print("[ ");
  Serial.print(recv_x);
  Serial.print(", ");
  Serial.print(recv_y);
  Serial.print(", ");
  Serial.print(target_x);
  Serial.print(", ");
  Serial.print(target_y);
  Serial.println(" ]");
  
  mqtt_client.publish("esp32_controller_1/response", "[ESP32_CONTROLLER_1] Transmission OK.");

}

static void recvMsg(void *param) {
  long lastMsg = 0;
  char msg[50];

  mqtt_client.setServer(mqtt_server, mqtt_port);
  mqtt_client.setCallback(callback);
  while(true){
    if (!mqtt_client.connected()) {
      reconnect();
    }
    mqtt_client.loop();
    if(cur_x > target_x){
      cur_x--;
      pwm.setPWM(0, 0, cur_x);
    }else if(cur_x < target_x){
      cur_x++;
      pwm.setPWM(0, 0, cur_x);
    }
    delay(10);

    if(cur_y > target_y){
      cur_y--;
      pwm.setPWM(1, 0, cur_y);
    }else if(cur_y < target_y){
      cur_y++;
      pwm.setPWM(1, 0, cur_y);
    }
    delay(10);
    Serial.print("[PWM] (X, Y) = (");
    Serial.print(cur_x);
    Serial.print(", ");
    Serial.print(cur_y);
    Serial.println(")");
  }
  vTaskDelete(NULL);
}

void setup() {
  Serial.begin(115200);
  pinMode(DHTPIN, OUTPUT);
  pinMode(ILLPIN, INPUT);
  dht.setup(DHTPIN, DHTesp::DHT11);
  connection_init();
  pwm_setup();
  
  xTaskCreate(recvMsg, "Recv", 10000, NULL, 1, NULL);
  xTaskCreate(sendData, "Send", 10000, NULL, 1, NULL);
}

void loop() {
  delay(200);
}
