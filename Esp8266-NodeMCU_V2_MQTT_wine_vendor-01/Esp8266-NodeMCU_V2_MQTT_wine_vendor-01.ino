// Реле подлкючено к пину GPIO0 (D3)
// Датчик жидкости к пину GPIO2 (D4)
// Датчик влажности к пину GPI14 (D5)

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 32 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
//#define OLED_RESET     4 // Reset pin # (or -1 if sharing Arduino reset pin)
#define OLED_RESET    LED_BUILTIN // 12
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define RELAY_PIN 0
#define HALL_SENSOR 2
#define HUM_PIN 14

const char *topic_pub1 = "wine_vendor/knygarnya111/device0001/state";
const char *topic_sub1 = "wine_vendor/knygarnya111/device0001/ctl";

const char *ssid =  "KNYGARIUM";  // Имя вайфай точки доступа
const char *pass =  "knygarium"; // Пароль от точки доступа

const char *mqtt_server = "korotach.com"; // Имя сервера MQTT
const int mqtt_port = 1883; // Порт для подключения к серверу MQTT
const char *mqtt_user = "slkrt"; // Логи от сервер
const char *mqtt_pass = "Vfktymrbq35"; // Пароль от сервера

bool RelayState = false;
int tm=300;
int FillDelay=4188;
int Filled = 50000;
volatile int NbTopsFan = 0; //measuring the rising edges of the signal
int Calc = 0;
// bool Ready = true;
String Status = "Ready";
bool Pump_On = false;
int val = 0;
boolean invert = true;
int scroll_type = 0;
String account = "";
String recv_sequence = "";
int ping_time = 0;

// Функция получения данных от сервера

void callback(const MQTT::Publish& pub)
{
  Serial.print(pub.topic());   // выводим в сериал порт название топика
  Serial.print(" => ");
  Serial.println(pub.payload_string()); // выводим в сериал порт значение полученных данных

  char payload[200];
  pub.payload_string().toCharArray(payload, 200);
  
  if(String(pub.topic()) == topic_sub1) // проверяем из нужного ли нам топика пришли данные 
  {
  if (Status == "Ready" or Status == "NO CONNECT") {
    DynamicJsonBuffer jsonBuffer(200);
    JsonObject& root = jsonBuffer.parseObject(payload);
    if (!root.success()) {
      Serial.println("JSON parsing failed!");
      return;
    } else {
        int recv_sequence1 = root["recv_sequence"];
//        Serial.println("{\"recv_seq1\": \"" + String(recv_sequence1) + "\"}");
        if (recv_sequence1 != 111) {
          recv_sequence = recv_sequence1;
          String account1 = root["account"];
          account = account1;
          Serial.println(account);
          scrolltext(account, 2);
          Pump_On = true;
        } else {  // ping from python script
          ping_time = millis();
        }
      }
    }
  }
}


WiFiClient wclient;      
PubSubClient client(wclient, mqtt_server, mqtt_port);

void ICACHE_RAM_ATTR rpm()     //This is the function that the interupt calls 
{ 
  NbTopsFan++;  //This function measures the rising and falling edge of the hall effect sensors signal
} 

void setup() {
  pinMode(HALL_SENSOR, INPUT_PULLUP);
  Serial.begin(115200);
  attachInterrupt(digitalPinToInterrupt (HALL_SENSOR), rpm, RISING);
  delay(10);
  Serial.println();
  Serial.println();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  pinMode(HUM_PIN, INPUT);
//  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for 128x32
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C, true)) {
    Serial.println(F("SSD1306 allocation failed"));
//    for(;;); // Don't proceed, loop forever
  }
//  ping_time = millis();
  display.display();
  delay(2000); // Pause for 2 seconds

  // Clear the buffer
  display.clearDisplay();
}

void loop() {
  // подключаемся к wi-fi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("Connecting to ");
    Serial.print(ssid);
    Serial.println("...");
    WiFi.begin(ssid, pass);

    if (WiFi.waitForConnectResult() != WL_CONNECTED)
      return;
    Serial.println("WiFi connected");
  }

  // подключаемся к MQTT серверу
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      Serial.println("Connecting to MQTT server");
      if (client.connect(MQTT::Connect("device0001")
                         .set_auth(mqtt_user, mqtt_pass))) {
        Serial.println("Connected to MQTT server");
        client.set_callback(callback);
        client.subscribe(topic_sub1); // подписывааемся по топик с данными для насоса крипто-бармена
      } else {
        Serial.println("Could not connect to MQTT server");   
      }
    }

    if (client.connected()){
      client.loop();
      if (Status == "Ready" and Pump_On) {
//      if (Pump_On) {
        FillGlass(FillDelay);
      }
      ReadySend();
    }  
  }
} // конец основного цикла


// Функция отправки в соотв. топик MQTT брокера признака готовности устройства
void ReadySend(){
  if (tm<=0)
  {
//    Status = "Ready";
    val = digitalRead(HUM_PIN);
    Serial.println("val = " + String(val));
    if (val) {
      Status = "Empty";
    } else {
        int ping_time1 = millis();
        if (ping_time1 - ping_time < 10000) {
          Status = "Ready";
        } else {
            Status = "NO CONNECT";
//          Status = "NO CONNECT " + String(int((ping_time1 - ping_time)/1000)) + " sec";
//          client.publish(topic_pub1, "{\"ping interval is \": \"" + String(ping_time1 - ping_time) + "\"}");
        }
    }
//    client.publish(topic_pub1, Status + " val = " + val);
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
    Serial.println(Status);
//    invert = !invert;
//    display.invertDisplay(invert);
    scrolltext(Status, 2);
//    display.invertDisplay(false);
//    scrolltext(Status, 2);
    tm = 300;  // пауза меду отправками признака готовности около 3 секунд
  }
  tm--; 
  delay(10);  
}

//Функция налива 100 грамм
void FillGlass(int FDelay){
  Status = "Busy";
//  client.publish(topic_pub1, Status);
  client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
//  scrolltext(Status, 2);
  digitalWrite(RELAY_PIN, true);
  NbTopsFan = 0;
  Calc = 0;
  delay(FDelay);
  digitalWrite(RELAY_PIN, false);
  ping_time = millis();
  Calc = NbTopsFan;
  if (Calc < 380) {
    Status = "Error";
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\", \"filled\": \"" + String(Calc) + "\"}");
    for (int i=0; i <= 12; i++) {
      scroll_type = 1;
      invert = !invert;
      display.invertDisplay(invert);
      scrolltext(Status, 3);  
      delay(250);
    }
    ping_time = millis();
  } else {
    Status = "OK";
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\", \"filled\": \"" + String(Calc) + "\", \"account\": \"" + account + "\", \"recv_sequence\": " + recv_sequence + "}");        
    scrolltext(Status, 3);
    delay(3000);
    scrolltext("THANK YOU!", 2);
    delay(3000);
    ping_time = millis();
  }
//  client.publish(topic_pub1, "Filled " + String(Calc));
  delay(50);
//  Status = "Ready";
//  client.publish(topic_pub1, Status);
//  client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
  Pump_On = false;
  scrolltext(Status, 2);
}

void scrolltext(String text, int size) {
  display.clearDisplay();

  display.setTextSize(size); // Draw 2X-scale text
  display.setTextColor(WHITE);
  display.setCursor(5, 3);
//  display.println(F("test"));
  display.println(text);
  display.display();      // Show initial text
  delay(100);
  switch(scroll_type) {
  // Scroll in various directions, pausing in-between:
  case 1:
//    display.stopscroll();
    display.startscrollright(0x00, 0x0F);
    break;
//  delay(2000);
  case 2:
//    display.stopscroll();
//    break;
//  delay(1000);
//  case 3:
    display.startscrollleft(0x00, 0x0F);
    break;
//  delay(2000);
  case 3:
//    display.stopscroll();
//    break;
//  delay(1000);
//  case 5:
    display.startscrolldiagright(0x00, 0x07);
    break;
//  delay(2000);
  case 4:
    display.startscrolldiagleft(0x00, 0x07);
    break;
//  delay(2000);
  default:
//    display.stopscroll();
    scroll_type = 0;
    invert = !invert;
    display.invertDisplay(invert);
//  delay(1000);
  }
  scroll_type += 1; 
}
