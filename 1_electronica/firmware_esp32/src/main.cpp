// =====================================================================
// Monitor de cadena de frio - ESP32 (simulado en Wokwi)
//
// Lee 3 termistores NTC por el ADC interno y emite UNA fila CSV por ciclo:
//
//   t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,alarma,Origen
//
//   t_ms    : instante de la lectura, en ms desde el arranque (millis()).
//   adc_i   : cuenta cruda del ADC de 12 bits (0-4095) del canal i.
//   T_i     : temperatura del canal i en grados C (NA si la lectura no es valida).
//   alarma  : 1 si algun canal esta fuera de [TEMP_MIN, TEMP_MAX] o no es valido.
//   Origen  : siempre "SIMULADO" (el circuito corre en Wokwi).
//
// Las lineas que empiezan por '#' son mensajes informativos, no datos.
// =====================================================================

#include <Arduino.h>
#include <math.h>

// -------------------------------
// CONFIGURACION DE PINES
// -------------------------------

const int LED_PIN = 2;

const int NUM_SENSORES = 3;

const int NTC_PINS[NUM_SENSORES] = {
    34, 35, 32
};

// -------------------------------
// PERIODO DE MUESTREO
// -------------------------------

// Ts = 1000 ms. Justificacion numerica (R2): 1_electronica/resultados/justificacion_Ts.md
// (intervalo admisible ~10 ms <= Ts <= 3 s, generado por justificacion_ts.py).
const unsigned long TS_MS = 1000;

// -------------------------------
// PARAMETROS DE LOS TERMISTORES
// -------------------------------
//
// *** CONVERSION PROVISIONAL ***
// La conversion ADC -> temperatura usa la ecuacion beta con los valores
// NOMINALES del termistor (R0 = 10 kohm, beta = 3950 K) y del resistor fijo
// del modulo de Wokwi (10 kohm). Es PROVISIONAL: se reemplazara por los
// coeficientes de calibracion propios de cada canal (R6 / R19).

const float R0 = 10000.0;           // Resistencia del NTC a 25 C [ohm]
const float BETA = 3950.0;          // Coeficiente beta [K]
const float R_FIJO = 10000.0;       // Resistor fijo del divisor [ohm]
const float TEMP_REFERENCIA_K = 298.15;

const float ADC_MAX = 4095.0;

// Lecturas en los extremos del ADC = sensor desconectado o en corto.
const int ADC_LIMITE_INFERIOR = 5;
const int ADC_LIMITE_SUPERIOR = 4090;

// -------------------------------
// LIMITES DE TEMPERATURA
// -------------------------------

const float TEMP_MIN = 2.0;
const float TEMP_MAX = 8.0;

// -------------------------------
// CONVERSION ADC A TEMPERATURA (PROVISIONAL)
// -------------------------------

float adcATemperatura(int adcValue) {

    // Detectar lecturas extremas (sensor desconectado o en corto)
    if (adcValue <= ADC_LIMITE_INFERIOR || adcValue >= ADC_LIMITE_SUPERIOR) {
        return NAN;
    }

    // Divisor 3V3 - R_FIJO - nodo - NTC - GND:
    //   adc / ADC_MAX = R_ntc / (R_FIJO + R_ntc)
    float resistencia =
        R_FIJO * adcValue / (ADC_MAX - adcValue);

    float temperatura = 1.0 /
        (
            log(resistencia / R0) / BETA
            + 1.0 / TEMP_REFERENCIA_K
        ) - 273.15;

    // Rechazar temperaturas fisicamente fuera del
    // intervalo de trabajo establecido para el proyecto
    if (temperatura < 0.0 || temperatura > 40.0) {
        return NAN;
    }

    return temperatura;
}

// -------------------------------
// CONFIGURACION INICIAL
// -------------------------------

unsigned long proximoMuestreo = 0;

void setup() {

    pinMode(LED_PIN, OUTPUT);

    Serial.begin(115200);
    analogReadResolution(12);

    Serial.println("# Sistema de cadena de frio iniciado (SIMULADO)");
    Serial.println("t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,alarma,Origen");

    proximoMuestreo = millis();
}

// -------------------------------
// PROGRAMA PRINCIPAL
// -------------------------------

void loop() {

    // Muestreo con periodo fijo: el siguiente instante se calcula sumando TS_MS
    // al anterior, asi el tiempo de procesamiento no acumula retraso.
    if ((long)(millis() - proximoMuestreo) < 0) {
        return;
    }

    unsigned long tMs = millis();
    proximoMuestreo += TS_MS;

    int adc[NUM_SENSORES];
    float temperatura[NUM_SENSORES];
    bool alarma = false;

    // Leer todos los canales primero (lo mas juntos posible en el tiempo)
    for (int i = 0; i < NUM_SENSORES; i++) {
        adc[i] = analogRead(NTC_PINS[i]);
    }

    // Convertir y evaluar la alarma
    for (int i = 0; i < NUM_SENSORES; i++) {

        temperatura[i] = adcATemperatura(adc[i]);

        if (isnan(temperatura[i])) {
            alarma = true;  // canal no valido
        } else if (temperatura[i] < TEMP_MIN || temperatura[i] > TEMP_MAX) {
            alarma = true;  // fuera del rango 2-8 C
        }
    }

    // Una fila CSV por ciclo
    Serial.print(tMs);

    for (int i = 0; i < NUM_SENSORES; i++) {
        Serial.print(",");
        Serial.print(adc[i]);
    }

    for (int i = 0; i < NUM_SENSORES; i++) {
        Serial.print(",");
        if (isnan(temperatura[i])) {
            Serial.print("NA");
        } else {
            Serial.print(temperatura[i], 2);
        }
    }

    Serial.print(",");
    Serial.print(alarma ? 1 : 0);
    Serial.println(",SIMULADO");

    // El LED se enciende si hay alarma
    digitalWrite(LED_PIN, alarma ? HIGH : LOW);
}
