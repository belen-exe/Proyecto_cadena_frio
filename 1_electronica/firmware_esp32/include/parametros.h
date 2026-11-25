// =====================================================================
// ARCHIVO GENERADO por 1_electronica/generar_parametros.py - NO EDITAR A MANO.
// Origen: E1_calibracion/resultados/coeficientes_calibracion.json
//         E3_eventos/resultados/parametros_detector.json
// Datos SIMULADOS.
// =====================================================================
#pragma once

// ---- Calibración de E1 (estructura M2):  1/T_K = THETA[i][0] + THETA[i][1]·L ----
const float THETA[3][2] = {
    {3.3556580531e-03f, 2.5258270338e-04f},
    {3.3563676551e-03f, 2.5402319555e-04f},
    {3.3529811665e-03f, 2.5487010037e-04f}
};

// ---- Detector PCA de E3 (fijado solo con entrenamiento.csv) ----
// VENTANA: promedio móvil [muestras]; K_COMP: componentes retenidas;
// K_PERSISTENCIA: muestras anómalas seguidas para encender la alarma.
const int VENTANA = 10;
const int K_COMP = 1;
const int K_PERSISTENCIA = 3;

// Media y desviación de cada sensor [°C] y autovalores retenidos.
const float MU[3] = {4.9474940434e+00f, 5.0970056308e+00f, 4.7536089305e+00f};
const float S[3] = {2.1689879787e-01f, 2.1260371488e-01f, 2.1309424794e-01f};
const float LAMBDA[K_COMP] = {2.9643050157e+00f};

// P_RET[sensor][componente]
const float P_RET[3][K_COMP] = {
    {5.7707060031e-01f},
    {5.7741200760e-01f},
    {5.7756808753e-01f}
};

const float UMBRAL_T2 = 2.5488212594e+00f;
const float UMBRAL_Q = 1.7806063058e-01f;
