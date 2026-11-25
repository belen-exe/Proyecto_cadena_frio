// =====================================================================
// Monitor de cadena de frio - ESP32 (simulado en Wokwi)        R2 + R19
//
// En CADA ciclo (Ts = 1 s), sin ayuda del computador:
//   1. lee los 3 canales del ADC;
//   2. temperatura calibrada de cada canal con los coeficientes de E1:
//          L = ln(adc / (4095 - adc)),   T = 1/(THETA0 + THETA1*L) - 273.15
//   3. detector de E3: promedio movil de VENTANA muestras, estandariza con MU y S,
//      proyecta sobre las componentes P_RET, calcula T2 y Q, compara con los
//      umbrales y aplica la persistencia K;
//   4. si hay alarma: enciende el LED y escribe un mensaje "# ALARMA" por serie.
//
// Todos los numeros vienen de include/parametros.h, que genera
// 1_electronica/generar_parametros.py a partir de los JSON de E1 y E3.
//
// Una fila CSV por ciclo:
//   t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,T2,Q,alarma,t_proc_us,Origen
//
//   T_i       : temperatura CALIBRADA del canal i [C] (NA si el canal no es valido)
//   T2, Q     : estadisticos del detector (NA mientras la ventana no este llena)
//   alarma    : 1 si la muestra fue anomala K_PERSISTENCIA veces seguidas
//   t_proc_us : tiempo de lectura + calculo de este ciclo [us] (R20)
//
// Las lineas que empiezan por '#' son mensajes, no datos.
// =====================================================================

#include <Arduino.h>
#include <math.h>

#include "parametros.h"

// -------------------------------
// PINES Y MUESTREO
// -------------------------------

const int LED_PIN = 2;
const int NUM_SENSORES = 3;
const int NTC_PINS[NUM_SENSORES] = {34, 35, 32};

// Ts = 1000 ms. Justificacion (R2): 1_electronica/resultados/justificacion_Ts.md
const unsigned long TS_MS = 1000;

const float ADC_MAX = 4095.0f;
// Lecturas en los extremos del ADC = sensor desconectado o en corto.
const int ADC_LIMITE_INFERIOR = 5;
const int ADC_LIMITE_SUPERIOR = 4090;

// -------------------------------
// ESTADO DEL DETECTOR (se conserva entre ciclos)
// -------------------------------

float ventana[VENTANA][NUM_SENSORES];   // ultimas VENTANA temperaturas de cada canal
int posicion = 0;                       // donde se escribe la proxima muestra
int validasSeguidas = 0;                // ciclos seguidos con los 3 canales validos
int anomalasSeguidas = 0;               // ciclos seguidos con muestra anomala
bool alarmaAnterior = false;

unsigned long proximoMuestreo = 0;

// -------------------------------
// PASO 2: TEMPERATURA CALIBRADA (E1, estructura M2)
// -------------------------------

float temperaturaCalibrada(int adc, int canal) {
    if (adc <= ADC_LIMITE_INFERIOR || adc >= ADC_LIMITE_SUPERIOR) {
        return NAN;   // canal desconectado o en corto
    }
    float L = log(adc / (ADC_MAX - adc));
    return 1.0f / (THETA[canal][0] + THETA[canal][1] * L) - 273.15f;
}

// -------------------------------
// PASO 3: DETECTOR PCA (E3)
// Devuelve true si se pudo calcular (ventana llena); deja T2 y Q en las variables.
// -------------------------------

bool calcularDetector(float &T2, float &Q) {
    if (validasSeguidas < VENTANA) {
        return false;   // falta llenar la ventana con muestras validas
    }

    float z[NUM_SENSORES];
    for (int i = 0; i < NUM_SENSORES; i++) {
        // promedio movil de las ultimas VENTANA muestras
        float suma = 0.0f;
        for (int j = 0; j < VENTANA; j++) {
            suma += ventana[j][i];
        }
        float x = suma / VENTANA;
        // estandarizar con la media y la desviacion de entrenamiento
        z[i] = (x - MU[i]) / S[i];
    }

    // t = P^T z  (coordenada sobre cada componente retenida)
    // T2 = sum t^2 / lambda
    // z_reconstruida = P t ;  Q = ||z - z_reconstruida||^2
    float t[K_COMP];
    T2 = 0.0f;
    for (int c = 0; c < K_COMP; c++) {
        t[c] = 0.0f;
        for (int i = 0; i < NUM_SENSORES; i++) {
            t[c] += P_RET[i][c] * z[i];
        }
        T2 += t[c] * t[c] / LAMBDA[c];
    }

    Q = 0.0f;
    for (int i = 0; i < NUM_SENSORES; i++) {
        float reconstruida = 0.0f;
        for (int c = 0; c < K_COMP; c++) {
            reconstruida += P_RET[i][c] * t[c];
        }
        float residuo = z[i] - reconstruida;
        Q += residuo * residuo;
    }
    return true;
}

// -------------------------------
// CONFIGURACION INICIAL
// -------------------------------

void setup() {
    pinMode(LED_PIN, OUTPUT);
    Serial.begin(115200);
    analogReadResolution(12);

    Serial.println("# Monitor de cadena de frio con calibracion E1 y detector PCA E3 (SIMULADO)");
    Serial.print("# Memoria libre (heap) al iniciar [bytes]: ");
    Serial.println(ESP.getFreeHeap());
    Serial.println("t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,T2,Q,alarma,t_proc_us,Origen");

    proximoMuestreo = millis();
}

// -------------------------------
// PROGRAMA PRINCIPAL
// -------------------------------

void imprimirNumero(float valor, int decimales) {
    Serial.print(",");
    if (isnan(valor)) {
        Serial.print("NA");
    } else {
        Serial.print(valor, decimales);
    }
}

void loop() {
    // Muestreo con periodo fijo (el tiempo de calculo no acumula retraso)
    if ((long)(millis() - proximoMuestreo) < 0) {
        return;
    }
    unsigned long tMs = millis();
    proximoMuestreo += TS_MS;

    unsigned long inicioUs = micros();

    // ---- 1. Leer los 3 canales ----
    int adc[NUM_SENSORES];
    for (int i = 0; i < NUM_SENSORES; i++) {
        adc[i] = analogRead(NTC_PINS[i]);
    }

    // ---- 2. Temperatura calibrada ----
    float temperatura[NUM_SENSORES];
    bool desconectado = false;
    for (int i = 0; i < NUM_SENSORES; i++) {
        temperatura[i] = temperaturaCalibrada(adc[i], i);
        if (isnan(temperatura[i])) {
            desconectado = true;
        }
        ventana[posicion][i] = temperatura[i];
    }
    posicion = (posicion + 1) % VENTANA;
    // Si algun canal no es valido, la ventana tiene un hueco: hay que esperar
    // VENTANA ciclos validos seguidos para volver a calcular T2 y Q.
    validasSeguidas = desconectado ? 0 : validasSeguidas + 1;

    // ---- 3. Detector ----
    float T2 = NAN, Q = NAN;
    bool hayEstadistico = calcularDetector(T2, Q);
    bool fueraT2 = hayEstadistico && T2 > UMBRAL_T2;
    bool fueraQ = hayEstadistico && Q > UMBRAL_Q;
    bool anomala = desconectado || fueraT2 || fueraQ;

    anomalasSeguidas = anomala ? anomalasSeguidas + 1 : 0;
    bool alarma = anomalasSeguidas >= K_PERSISTENCIA;

    unsigned long tProcUs = micros() - inicioUs;

    // ---- 4. Salida: fila CSV, LED y mensaje ----
    Serial.print(tMs);
    for (int i = 0; i < NUM_SENSORES; i++) {
        Serial.print(",");
        Serial.print(adc[i]);
    }
    for (int i = 0; i < NUM_SENSORES; i++) {
        imprimirNumero(temperatura[i], 4);
    }
    imprimirNumero(T2, 4);
    imprimirNumero(Q, 4);
    Serial.print(",");
    Serial.print(alarma ? 1 : 0);
    Serial.print(",");
    Serial.print(tProcUs);
    Serial.println(",SIMULADO");

    digitalWrite(LED_PIN, alarma ? HIGH : LOW);

    if (alarma && !alarmaAnterior) {
        Serial.print("# ALARMA en t_ms=");
        Serial.print(tMs);
        Serial.print(": ");
        if (desconectado) Serial.print("sensor desconectado ");
        if (fueraQ) Serial.print("Q sobre el umbral (patron entre sensores roto, p. ej. tapa abierta) ");
        if (fueraT2) Serial.print("T2 sobre el umbral (los 3 sensores lejos de lo normal) ");
        Serial.println();
    } else if (!alarma && alarmaAnterior) {
        Serial.print("# Fin de la alarma en t_ms=");
        Serial.println(tMs);
    }
    alarmaAnterior = alarma;
}
