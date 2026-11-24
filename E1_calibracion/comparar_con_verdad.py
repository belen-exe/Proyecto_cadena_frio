"""
VERIFICACIÓN FINAL de E1 contra la verdad de la simulación.

Este es el ÚNICO script de E1 que lee VERDAD_NO_USAR.json. No forma parte del
análisis: solo comprueba, después de calibrar, que la calibración recupera la
relación real ADC -> temperatura de cada sensor simulado.

Uso:  python E1_calibracion/comparar_con_verdad.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import calibracion as cal  # noqa: E402
from comun import modelo_sensor as ms  # noqa: E402
from comun.estadistica import rmse  # noqa: E402

CARPETA = Path(__file__).resolve().parent
verdad = json.loads((CARPETA / "datos" / "VERDAD_NO_USAR.json").read_text(encoding="utf-8"))
coef = cal.cargar_coeficientes()
crudos = pd.read_csv(CARPETA / "datos" / "calibracion_E1.csv")

print("Comparación con la VERDAD de la simulación (solo verificación)\n")

# 1. Curva completa: ADC esperado (sin ruido) de cada sensor real en 0–45 °C
t_malla = np.linspace(0, 45, 451)
for c, parametros in enumerate(verdad["parametros_sensores"], start=1):
    sensor = ms.ParametrosSensor(**parametros)
    adc_continuo = ms.voltaje_a_adc_ideal(
        ms.resistencia_a_voltaje(ms.temperatura_a_resistencia(t_malla, sensor.r0_ohm, sensor.beta_k),
                                 sensor.r_fijo_ohm))
    error = t_malla - cal.predecir(adc_continuo, coef["estructura"], coef["canales"][str(c)]["theta"])
    print(f"Canal {c}: error de la curva calibrada vs curva real en 0-45 C: "
          f"max |e| = {np.max(np.abs(error)):.3f} C, RMSE = {rmse(error):.3f} C")

# 2. Puntos de prueba contra la temperatura REAL del baño (sin el error de la referencia)
reales = pd.DataFrame(verdad["puntos"])
puntos = crudos.groupby("punto").agg(
    tipo=("tipo", "first"), T_ref_C=("T_ref_C", "first"),
    **{f"adc_{c}": (f"adc_{c}", "mean") for c in (1, 2, 3)}).reset_index()
puntos = puntos.merge(reales[["punto", "T_bano_real_C"]], on="punto")
prueba = puntos[puntos["tipo"] == "prueba"]

print(f"\nError del termómetro de referencia en todos los puntos: "
      f"RMSE = {rmse(puntos['T_ref_C'] - puntos['T_bano_real_C']):.3f} C")
for c in (1, 2, 3):
    t_hat = cal.adc_a_temperatura_calibrada(prueba[f"adc_{c}"], c, coef)
    print(f"Canal {c}: RMSE en prueba vs temperatura REAL = {rmse(prueba['T_bano_real_C'] - t_hat):.3f} C "
          f"(vs referencia = {rmse(prueba['T_ref_C'] - t_hat):.3f} C)")
