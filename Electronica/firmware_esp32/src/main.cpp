
#include <Arduino.h>
#include <math.h>

// Pines
const int LED_PIN = 2;
const int NTC_PIN = 34;

// Parametros del termistor
const float BETA = 3950.0;
const float R0 = 10000.0;
const float TEMP_REFERENCIA_K = 298.15;

// ADC del ESP32
const float ADC_MAX = 4095.0;

// Limites de temperatura
const float TEMP_MIN = 2.0;
const float TEMP_MAX = 8.0;

void setup() {
    pinMode(LED_PIN, OUTPUT);

    Serial.begin(115200);
    analogReadResolution(12);

    Serial.println("Sistema de cadena de frio iniciado");
    Serial.println("ADC,Temperatura_C,Estado");
}

void loop() {
    // Leer el ADC
    int adcValue = analogRead(NTC_PIN);

    // Evitar divisiones por cero
    if (adcValue <= 0 || adcValue >= ADC_MAX) {
        Serial.println("ERROR: lectura ADC fuera de rango");
        digitalWrite(LED_PIN, HIGH);
        delay(1000);
        return;
    }

    // Calcular resistencia del NTC
    float resistencia = R0 * adcValue /
                        (ADC_MAX - adcValue);

    // Convertir resistencia a temperatura
    float temperatura = 1.0 /
        (log(resistencia / R0) / BETA + 1.0 / TEMP_REFERENCIA_K)
        - 273.15;

    // Comprobar el rango permitido
    bool fueraDeRango =
        temperatura < TEMP_MIN ||
        temperatura > TEMP_MAX;

    // Activar o apagar alarma
    digitalWrite(LED_PIN, fueraDeRango ? HIGH : LOW);

    // Mostrar datos
    Serial.print(adcValue);
    Serial.print(",");
    Serial.print(temperatura, 2);
    Serial.print(",");

    if (fueraDeRango) {
        Serial.println("ALARMA");
    } else {
        Serial.println("NORMAL");
    }

    delay(1000);
}
