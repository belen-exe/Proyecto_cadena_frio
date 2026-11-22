"""
Simulador del Experimento E1 (R4): datos de calibración ADC -> temperatura.

TODOS LOS DATOS QUE GENERA ESTE SCRIPT SON SIMULADOS (Origen = "SIMULADO").

Procedimiento simulado
----------------------
Los 3 sensores y el termómetro de referencia se sumergen JUNTOS en un mismo
recipiente con agua (baño agitado). Se parte de agua con hielo (≈ 0 °C) y se va
calentando por escalones hasta ≈ 45 °C. En cada escalón:
  1. se espera a que el baño se estabilice,
  2. se registran N_MUESTRAS lecturas del ADC de cada canal (Ts = 1 s),
  3. se anota la lectura del termómetro de referencia (resolución 0,1 °C).

Antes de medir se decide qué escalones son de CALIBRACIÓN (ajuste) y cuáles de
PRUEBA (solo evaluación): la columna `tipo` queda fija desde el inicio, así que los
puntos de prueba nunca intervienen en el ajuste.

Archivos generados en E1_calibracion/datos/
-------------------------------------------
  calibracion_E1.csv             datos crudos (una fila por muestra)
  instrumento_referencia.json    incertidumbre del termómetro de referencia y su fuente
  VERDAD_NO_USAR.json            temperaturas reales del baño y semilla. NO lo lea el análisis.

Uso:  python E1_calibracion/simulador_E1.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

CARPETA_DATOS = Path(__file__).resolve().parent / "datos"
ORIGEN = "SIMULADO"

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

SEMILLA = 101

TS_S = 1.0
N_MUESTRAS = 10                 # lecturas ADC por escalón
TIEMPO_ESTABILIZACION_S = 300   # espera entre escalones

# Escalones de temperatura nominales [°C]. Más densos en 0–10 °C (zona crítica).
ESCALONES_CALIBRACION = [
    0.3, 1.5, 2.2, 3.0, 4.5, 6.0, 7.5, 8.2, 9.0, 10.5,
    12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0,
    32.0, 34.0, 36.0, 38.0, 40.0, 42.0, 44.0, 45.0,
]
ESCALONES_PRUEBA = [0.8, 3.8, 6.8, 9.6, 15.0, 21.0, 27.0, 33.0, 39.0, 43.5]

# El baño no queda exactamente en el valor nominal.
DESVIO_ESCALON_C = 0.3          # uniforme ± este valor

# Fluctuación de la temperatura del baño entre muestras [°C] (agitación).
FLUCTUACION_BANO_C = 0.02

# Termómetro de referencia (supuestos tomados de una ficha técnica típica).
REFERENCIA = {
    "instrumento": "Termómetro digital de referencia con sonda (SIMULADO)",
    "resolucion_C": 0.1,
    "exactitud_C": 0.1,
    "fuente": (
        "Ficha técnica supuesta de un termómetro digital de laboratorio: exactitud "
        "±0,1 °C en 0–50 °C, resolución 0,1 °C. Valores SUPUESTOS para la simulación."
    ),
}
# Incertidumbre estándar combinada (tipo B): exactitud con distribución
# rectangular (a/√3) y resolución con distribución rectangular (q/√12).
U_EXACTITUD = REFERENCIA["exactitud_C"] / math.sqrt(3)
U_RESOLUCION = REFERENCIA["resolucion_C"] / math.sqrt(12)
U_REFERENCIA = math.sqrt(U_EXACTITUD ** 2 + U_RESOLUCION ** 2)

# Error real del termómetro en la simulación: normal con σ = exactitud/2.
SIGMA_ERROR_REFERENCIA = REFERENCIA["exactitud_C"] / 2


def main():
    rng = np.random.default_rng(SEMILLA)
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    escalones = sorted(
        [(t, "calibracion") for t in ESCALONES_CALIBRACION]
        + [(t, "prueba") for t in ESCALONES_PRUEBA]
    )

    filas = []
    verdad_puntos = []
    t_actual = 0.0

    for punto, (nominal, tipo) in enumerate(escalones, start=1):
        t_bano = nominal + rng.uniform(-DESVIO_ESCALON_C, DESVIO_ESCALON_C)
        t_bano = max(t_bano, 0.05)  # agua líquida

        # Lectura de la referencia (una por escalón), redondeada a su resolución
        lectura_ref = round(
            (t_bano + rng.normal(0, SIGMA_ERROR_REFERENCIA)) / REFERENCIA["resolucion_C"]
        ) * REFERENCIA["resolucion_C"]

        t_actual += TIEMPO_ESTABILIZACION_S
        temperaturas_muestras = t_bano + rng.normal(0, FLUCTUACION_BANO_C, size=N_MUESTRAS)

        adc = np.column_stack([
            ms.temperatura_a_adc(temperaturas_muestras, sensor, rng=rng)
            for sensor in ms.SENSORES
        ])

        for k in range(N_MUESTRAS):
            filas.append({
                "punto": punto,
                "tipo": tipo,
                "muestra": k + 1,
                "t_s": round(t_actual + k * TS_S, 3),
                "T_ref_C": round(lectura_ref, 1),
                "adc_1": adc[k, 0],
                "adc_2": adc[k, 1],
                "adc_3": adc[k, 2],
                "Origen": ORIGEN,
            })
        t_actual += N_MUESTRAS * TS_S

        verdad_puntos.append({
            "punto": punto,
            "tipo": tipo,
            "T_nominal_C": nominal,
            "T_bano_real_C": round(t_bano, 4),
        })

    tabla = pd.DataFrame(filas)
    ruta = CARPETA_DATOS / "calibracion_E1.csv"
    tabla.to_csv(ruta, index=False)

    referencia = dict(REFERENCIA)
    referencia.update({
        "u_exactitud_C": round(U_EXACTITUD, 4),
        "u_resolucion_C": round(U_RESOLUCION, 4),
        "u_estandar_combinada_C": round(U_REFERENCIA, 4),
        "U_expandida_k2_C": round(2 * U_REFERENCIA, 4),
        "Origen": ORIGEN,
    })
    (CARPETA_DATOS / "instrumento_referencia.json").write_text(
        json.dumps(referencia, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    verdad = {
        "ADVERTENCIA": "Valores reales de la simulación. Ningún análisis debe leer este archivo.",
        "Origen": ORIGEN,
        "semilla": SEMILLA,
        "fluctuacion_bano_C": FLUCTUACION_BANO_C,
        "sigma_error_referencia_C": SIGMA_ERROR_REFERENCIA,
        "parametros_sensores": [s.como_dict() for s in ms.SENSORES],
        "ruido_adc_cuentas": ms.RUIDO_ADC_CUENTAS,
        "puntos": verdad_puntos,
    }
    (CARPETA_DATOS / "VERDAD_NO_USAR.json").write_text(
        json.dumps(verdad, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    n_cal = len(ESCALONES_CALIBRACION)
    n_pru = len(ESCALONES_PRUEBA)
    print(f"Generado: {ruta.relative_to(RAIZ_REPO)}  ({len(tabla)} filas; "
          f"{n_cal} puntos de calibración y {n_pru} de prueba)")
    print(f"Puntos en 0-10 C: calibración {sum(t <= 10 for t in ESCALONES_CALIBRACION)}, "
          f"prueba {sum(t <= 10 for t in ESCALONES_PRUEBA)}")
    print(f"Incertidumbre estándar de la referencia: {U_REFERENCIA:.3f} C")
    print("Generado: E1_calibracion/datos/instrumento_referencia.json, VERDAD_NO_USAR.json")


if __name__ == "__main__":
    main()
