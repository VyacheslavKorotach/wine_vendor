// Реле подлкючено к пину IO2
// Датчик жидкости к пину IO0

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 0
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

const char *ssid =  "SK-Home";  // Имя вайфай точки доступа
const char *pass =  "vfksi111"; // Пароль от точки доступа

const char *mqtt_server = "korotach.com"; // Имя сервера MQTT
const int mqtt_port = 1883; // Порт для подключения к серверу MQTT
const char *mqtt_user = "slkrt"; // Логи от сервер
const char *mqtt_pass = "Vfktymrbq35"; // Пароль от сервера

#define BUFFER_SIZE 100

bool LedState = false;
int tm=300;
float temp=0;

// Функция получения данных от сервера

void callback(const MQTT::Publish& pub)
{
  Serial.print(pub.topic());   // выводим в сериал порт название топика
  Serial.print(" => ");
  Serial.print(pub.payload_string()); // выводим в сериал порт значение полученных данных
  
  String payload = pub.payload_string();
  
  if(String(pub.topic()) == "cryptobarman/00001/ctl") // проверяем из нужного ли нам топика пришли данные 
  {
  int stled = payload.toInt(); // преобразуем полученные данные в тип integer
  digitalWrite(2,!stled);  //  включаем или выключаем светодиод в зависимоти от полученных значений данных
  }
}



WiFiClient wclient;      
PubSubClient client(wclient, mqtt_server, mqtt_port);

void setup() {
  
  sensors.begin();
  Serial.begin(115200);
  delay(10);
  Serial.println();
  Serial.println();
  pinMode(2, OUTPUT);
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
      if (client.connect(MQTT::Connect("arduinoClient2")
                         .set_auth(mqtt_user, mqtt_pass))) {
        Serial.println("Connected to MQTT server");
        client.set_callback(callback);
        client.subscribe("cryptobarman/00001/ctl"); // подписывааемся по топик с данными для светодиода
      } else {
        Serial.println("Could not connect to MQTT server");   
      }
    }

    if (client.connected()){
      client.loop();
      TempSend();
  }
  
}
} // конец основного цикла


// Функция отправки показаний с термодатчика
void TempSend(){
  if (tm==0)
  {
  sensors.requestTemperatures();   // от датчика получаем значение температуры
  float temp = sensors.getTempCByIndex(0);
  client.publish("cryptobarman/00001/filled",String(temp)); // отправляем в топик для термодатчика значение температуры
  Serial.println(temp);
  tm = 300;  // пауза меду отправками значений температуры  коло 3 секунд
  }
  tm--; 
  delay(10);  
}
