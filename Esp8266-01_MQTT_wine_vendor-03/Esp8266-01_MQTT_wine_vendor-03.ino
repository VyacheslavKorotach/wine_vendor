// Реле подлкючено к пину IO0
// Датчик жидкости к пину IO2
// Датчик влажности к пину IO1 (TXD0)

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define RELAY_PIN 0
#define HALL_SENSOR 2
#define HUM_PIN 1

const char *topic_pub1 = "wine_vendor/knygarnya111/device0001/state";
const char *topic_sub1 = "wine_vendor/knygarnya111/device0001/ctl";

const char *ssid =  "SK-Home";  // Имя вайфай точки доступа
const char *pass =  "vfksi111"; // Пароль от точки доступа

const char *mqtt_server = "korotach.com"; // Имя сервера MQTT
const int mqtt_port = 1883; // Порт для подключения к серверу MQTT
const char *mqtt_user = "slkrt"; // Логи от сервер
const char *mqtt_pass = "Vfktymrbq35"; // Пароль от сервера

bool RelayState = false;
int tm=300;
int FillDelay=8000;
int Filled = 2800000;
volatile int NbTopsFan = 0; //measuring the rising edges of the signal
int Calc = 0;
// bool Ready = true;
String Status = "Ready";
bool Pump_On = false;
int val = 0;

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
  if (Status == "Ready") {
    Pump_On = true;
  }
  DynamicJsonBuffer jsonBuffer(200);
  JsonObject& root = jsonBuffer.parseObject(payload);
  if (!root.success()) {
    Serial.println("JSON parsing failed!");
    return;
  } else {
      String account = root["account"];
      Serial.println(account);
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
    Status = "Ready";
    val = digitalRead(HUM_PIN);
    Serial.println("val = " + String(val));
    if (val) {
      Status = "Empty";
    }
//    client.publish(topic_pub1, Status + " val = " + val);
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
    Serial.println(Status);
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
  digitalWrite(RELAY_PIN, true);
  NbTopsFan = 0;
  Calc = 0;
  delay(FDelay);
  digitalWrite(RELAY_PIN, false);
  Calc = NbTopsFan;
  if (Calc < 500) {
    Status = "Error";
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\", \"filled\": \"" + String(Calc) + "\"}");
//    client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
//    client.publish(topic_pub1, "Filled " + String(Calc));    
  } else {
    Status = "OK";
    client.publish(topic_pub1, "{\"status\": \"" + Status + "\", \"filled\": \"" + String(Calc) + "\"}");    
  }
//  client.publish(topic_pub1, "Filled " + String(Calc));
  delay(50);
  Status = "Ready";
//  client.publish(topic_pub1, Status);
  client.publish(topic_pub1, "{\"status\": \"" + Status + "\"}");
  Pump_On = false;
}
