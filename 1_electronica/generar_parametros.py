"""
R19 - Copia al firmware lo que se escogió en los experimentos.

Lee:
  E1_calibracion/resultados/coeficientes_calibracion.json   (θ0, θ1 de cada canal)
  E3_eventos/resultados/parametros_detector.json            (μ, s, P, λ, k, umbrales, K, ventana)
y escribe:
  1_electronica/firmware_esp32/include/parametros.h

Así los números del ESP32 son EXACTAMENTE los de Python y no se copian a mano.
Hay que volver a ejecutarlo (y recompilar) si se repite E1 o el entrenamiento de E3.

Uso:  python 1_electronica/generar_parametros.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_E1 = RAIZ / "E1_calibracion" / "resultados" / "coeficientes_calibracion.json"
RUTA_E3 = RAIZ / "E3_eventos" / "resultados" / "parametros_detector.json"
RUTA_H = RAIZ / "1_electronica" / "firmware_esp32" / "include" / "parametros.h"


def lista(valores):
    """[1.0, 2.0] -> '{1.0000000000e+00f, 2.0000000000e+00f}' (constantes float de C++)."""
    return "{" + ", ".join(f"{v:.10e}f" for v in valores) + "}"


def main():
    e1 = json.loads(RUTA_E1.read_text(encoding="utf-8"))
    e3 = json.loads(RUTA_E3.read_text(encoding="utf-8"))
    assert e1["estructura"] == "M2_beta", "El firmware implementa la estructura M2: 1/T_K = θ0 + θ1·L"

    k = e3["k"]
    thetas = [e1["canales"][str(c)]["theta"] for c in (1, 2, 3)]
    # P se guarda por filas (sensor) y columnas (componente): se toman las k primeras columnas.
    p_ret = [fila[:k] for fila in e3["P"]]

    texto = f"""// =====================================================================
// ARCHIVO GENERADO por 1_electronica/generar_parametros.py - NO EDITAR A MANO.
// Origen: {RUTA_E1.relative_to(RAIZ).as_posix()}
//         {RUTA_E3.relative_to(RAIZ).as_posix()}
// Datos SIMULADOS.
// =====================================================================
#pragma once

// ---- Calibración de E1 (estructura M2):  1/T_K = THETA[i][0] + THETA[i][1]·L ----
const float THETA[3][2] = {{
    {lista(thetas[0])},
    {lista(thetas[1])},
    {lista(thetas[2])}
}};

// ---- Detector PCA de E3 (fijado solo con entrenamiento.csv) ----
// VENTANA: promedio móvil [muestras]; K_COMP: componentes retenidas;
// K_PERSISTENCIA: muestras anómalas seguidas para encender la alarma.
const int VENTANA = {e3['ventana_suavizado_s']};
const int K_COMP = {k};
const int K_PERSISTENCIA = {e3['K_persistencia']};

// Media y desviación de cada sensor [°C] y autovalores retenidos.
const float MU[3] = {lista(e3['mu'])};
const float S[3] = {lista(e3['s'])};
const float LAMBDA[K_COMP] = {lista(e3['autovalores'][:k])};

// P_RET[sensor][componente]
const float P_RET[3][K_COMP] = {{
    {lista(p_ret[0])},
    {lista(p_ret[1])},
    {lista(p_ret[2])}
}};

const float UMBRAL_T2 = {e3['umbral_T2']:.10e}f;
const float UMBRAL_Q = {e3['umbral_Q']:.10e}f;
"""
    RUTA_H.write_text(texto, encoding="utf-8")
    print(f"Generado: {RUTA_H.relative_to(RAIZ)}  (k = {k}, ventana = {e3['ventana_suavizado_s']}, "
          f"K = {e3['K_persistencia']})")


if __name__ == "__main__":
    main()
