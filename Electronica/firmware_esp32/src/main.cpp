
#include <Arduino.h>

// Pin del LED externo que utilizaremos en la simulación
const int LED_PIN = 2;

void setup() {
    // Se ejecuta una sola vez al iniciar el ESP32
    pinMode(LED_PIN, OUTPUT);

    Serial.begin(115200);
    Serial.println("Sistema de cadena de frio iniciado");
}

void loop() {
    // Encender LED
    digitalWrite(LED_PIN, HIGH);
    Serial.println("LED encendido");
    delay(1000);

    // Apagar LED
    digitalWrite(LED_PIN, LOW);
    Serial.println("LED apagado");
    delay(1000);
}
