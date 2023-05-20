#include <Arduino.h>
#include <Wifi.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include "env.h" 

#define endpoint ""

#define presencePin 24
#define fanPin 22
#define lightPin 23



float getTemp(){

  return random(21.1, 33.1);
}

float getpresence(){

  return random(0,1);
}

void setup() {

  Serial.begin(9600);

	pinMode(fanPin,OUTPUT);
  pinMode(lightPin,OUTPUT);
  pinMode(presencePin, OUTPUT);

	// WiFi_SSID and WIFI_PASS in env.h
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("");

	// Connect to the wifi
  Serial.println("Connecting...");
  while(WiFi.status() != WL_CONNECTED)
   {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to the WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop()
 {
  //Check WiFi connection status
  if(WiFi.status()== WL_CONNECTED){
    Serial.println("");
    Serial.println("");
    HTTPClient http;
  
    // Establish a connection to the server
    String url = "https://" + String(endpoint) + "/temperature";
    http.begin(url);
    http.addHeader("Content-length", "24");
    http.addHeader("Content-type", "application/json");



    // Specify content-type header
    //http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<1024> docput;
    String httpRequestData;

    // Serialise JSON object into a string to be sent to the API
  

    docput["temperature"] = getTemp();
    docput["presence"] = getpresence();
  

    // Convert JSON document, doc, to a string and copy into the httpRequestData
    serializeJson(docput, httpRequestData);

    // Send HTTP PUT request
    int httpResponseCode = http.PUT(httpRequestData);
    String http_response;

    // Checking result of PUT request. A negative response code means server wasn't reached
    if (httpResponseCode>0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);

      Serial.print("HTTP Response from server: ");
      http_response = http.getString();
      Serial.println(http_response);
    }
    else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();


    http.end();   
    http.begin(url);
    httpResponseCode = http.GET();

    Serial.println("");
    Serial.println("");

    if (httpResponseCode>0) {
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);

        Serial.print("Response from server: ");
        http_response = http.getString();
        Serial.println(http_response);
      }
      else {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode);
    }
 
    StaticJsonDocument<1024> docget;

    DeserializationError error = deserializeJson(docget, http_response);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }
    
    bool temp = docget["fan"]; 
    bool light= docget["light"]; 
    bool presence= docget["presence"]; 

    digitalWrite(fanPin,temp);
    digitalWrite(lightPin,light);
    digitalWrite(presencePin,presence);
    
    // Free resources
    http.end();
  }
  else {
    Serial.println("WiFi is Disconnected");
  }
}





