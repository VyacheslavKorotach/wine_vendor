// Реле подлкючено к пину IO0
// Датчик жидкости к пину IO2

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

//#define ONE_WIRE_BUS 2
#define RELAY_PIN 0
#define HALL_SENSOR 2

//OneWire oneWire(ONE_WIRE_BUS);
//DallasTemperature sensors(&oneWire);

const char *ssid =  "SK-Home";  // Имя вайфай точки доступа
const char *pass =  "vfksi111"; // Пароль от точки доступа

const char *mqtt_server = "korotach.com"; // Имя сервера MQTT
const int mqtt_port = 1883; // Порт для подключения к серверу MQTT
const char *mqtt_user = "slkrt"; // Логи от сервер
const char *mqtt_pass = "Vfktymrbq35"; // Пароль от сервера

#define BUFFER_SIZE 100

bool RelayState = false;
int tm=300;
int FillDelay=200;
int Filled = 2800000;
float temp=0;
volatile int NbTopsFan = 0; //measuring the rising edges of the signal
int Calc = 0;

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
  RelayState = !(!stled);
  digitalWrite(RELAY_PIN, RelayState); //  включаем или выключаем реле в зависимоти от полученных значений данных (0 - выключить)
  NbTopsFan = 0;
  Calc = 0;
  }
}



WiFiClient wclient;      
PubSubClient client(wclient, mqtt_server, mqtt_port);

void ICACHE_RAM_ATTR rpm()     //This is the function that the interupt calls 
{ 
  NbTopsFan++;  //This function measures the rising and falling edge of the hall effect sensors signal
} 

void setup() {
  
//  sensors.begin();
  pinMode(HALL_SENSOR, INPUT_PULLUP);
  Serial.begin(115200);
  attachInterrupt(digitalPinToInterrupt (HALL_SENSOR), rpm, RISING);
  delay(10);
  Serial.println();
  Serial.println();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
}

void loop() {
  sei();
//  cli();
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
        client.subscribe("cryptobarman/00001/ctl"); // подписывааемся по топик с данными для реле насоса
      } else {
        Serial.println("Could not connect to MQTT server");   
      }
    }

    if (client.connected()){
      
//      attachInterrupt(digitalPinToInterrupt (HALL_SENSOR), rpm, RISING);
      client.loop();
//      sei();      //Enables interrupts
//      delay (1000);   //Wait 1 second
//      cli();      //Disable interrupts
      TempSend();
      if (RelayState)
      {
        FillGlass();
      }
//      detachInterrupt(digitalPinToInterrupt (HALL_SENSOR)); 
  }
  
}
} // конец основного цикла


// Функция отправки показаний с термодатчика
void TempSend(){
  if (tm<=0)
  {
//  client.publish("cryptobarman/00001/filled",String(temp)); // отправляем в топик для термодатчика значение температуры
  client.publish("cryptobarman/00001/filled","active");
  Serial.println(temp);
  tm = 300;  // пауза меду отправками значений температуры  коло 3 секунд
  }
  tm--; 
  delay(10);  
}

//Функция налива 100 грамм
void FillGlass(){
  if (FillDelay <= 0)
  {
    RelayState = false;
    NbTopsFan = 0;
    FillDelay = 200;
    client.publish("cryptobarman/00001/filled",String(Calc));
  }
  FillDelay--;
  delay(10);
  if (Calc >= Filled)
  {
    RelayState = false;
    NbTopsFan = 0;
    client.publish("cryptobarman/00001/filled",String(Calc));
  }
  digitalWrite(RELAY_PIN, RelayState);
//  cli();      //Disable interrupts
//  Calc = (NbTopsFan * 60 / 73); //(Pulse frequency x 60) / 73Q, = flow rate in L/hour 
  Calc = NbTopsFan;
//  sei();
}
