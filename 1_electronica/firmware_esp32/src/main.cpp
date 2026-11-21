
#include <Arduino.h>
#include <math.h>

// -------------------------------
// CONFIGURACION DE PINES
// -------------------------------

const int LED_PIN = 2;

const int NTC_PINS[3] = {
    34, 35, 32
};

// -------------------------------
// PARAMETROS DE LOS TERMISTORES
// -------------------------------

const float R0 = 10000.0;
const float BETA = 3950.0;
const float TEMP_REFERENCIA_K = 298.15;

const float ADC_MAX = 4095.0;

// -------------------------------
// LIMITES DE TEMPERATURA
// -------------------------------

const float TEMP_MIN = 2.0;
const float TEMP_MAX = 8.0;

// -------------------------------
// CONVERSION ADC A TEMPERATURA
// -------------------------------


float leerTemperatura(int pin) {

    int adcValue = analogRead(pin);

    // Detectar lecturas extremas
    if (adcValue <= 5 || adcValue >= 4090) {
        return NAN;
    }

    float resistencia =
        R0 * adcValue / (ADC_MAX - adcValue);

    float temperatura = 1.0 /
        (
            log(resistencia / R0) / BETA
            + 1.0 / TEMP_REFERENCIA_K
        ) - 273.15;

    // Rechazar temperaturas físicamente fuera del
    // intervalo de trabajo establecido para el proyecto
    if (temperatura < 0.0 || temperatura > 40.0) {
        return NAN;
    }

    return temperatura;
}


// -------------------------------
// CONFIGURACION INICIAL
// -------------------------------

void setup() {

    pinMode(LED_PIN, OUTPUT);

    Serial.begin(115200);
    analogReadResolution(12);

    Serial.println("Sistema de cadena de frio iniciado");
    Serial.println("Tiempo_ms,Sensor,Temperatura_C,Estado,Origen");
}

// -------------------------------
// PROGRAMA PRINCIPAL
// -------------------------------

void loop() {

    bool alarmaGeneral = false;

    // Recorrer los tres sensores
    for (int i = 0; i < 3; i++) {

        float temperatura =
            leerTemperatura(NTC_PINS[i]);

        Serial.print(millis());
        Serial.print(",");
        Serial.print(i + 1);
        Serial.print(",");

        if (isnan(temperatura)) {
            Serial.print("NA,");
            Serial.print("ERROR,");
            alarmaGeneral = true;
        } else {
            bool fueraDeRango =
                temperatura < TEMP_MIN ||
                temperatura > TEMP_MAX;

            Serial.print(temperatura, 2);
            Serial.print(",");

            if (fueraDeRango) {
                Serial.print("ALARMA,");
                alarmaGeneral = true;
            } else {
                Serial.print("NORMAL,");
            }
        }

        Serial.println("SIMULADO");
    }

    // El LED se enciende si algun sensor detecta una alarma
    digitalWrite(
        LED_PIN,
        alarmaGeneral ? HIGH : LOW
    );

    delay(1000);
}
