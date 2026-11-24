"""
Estructuras de modelo para convertir la cuenta ADC en temperatura (R5) y uso de
los coeficientes de calibración obtenidos en E1 (R6).

Variables auxiliares, calculadas a partir de la cuenta ADC x (0–4095):

    u = x / 4095                         (cuenta normalizada, 0–1)
    L = ln( x / (4095 − x) )             (= ln(R_ntc / R_fijo) en el divisor)

L no necesita conocer R_fijo ni R0: esas constantes quedan absorbidas en los
coeficientes. Por eso las estructuras M2 y M3 sirven aunque cada sensor tenga
R0, β y R_fijo distintos del nominal.

Estructuras (complejidad creciente):

    M1  lineal en ADC          T     = θ0 + θ1·u                       (2 parámetros)
    M2  β (Steinhart-Hart 1)   1/T_K = θ0 + θ1·L                       (2 parámetros, forma física)
    M3  Steinhart-Hart cúbico  1/T_K = θ0 + θ1·L + θ2·L² + θ3·L³       (4 parámetros)

Todas son LINEALES en los parámetros θ: el modelo se escribe y = X·θ, con una
matriz de diseño X distinta para cada estructura, y se ajusta por mínimos cuadrados.
"""

import json
from pathlib import Path

import numpy as np

from comun import modelo_sensor as ms

RUTA_COEFICIENTES = (
    Path(__file__).resolve().parents[1] / "E1_calibracion" / "resultados" / "coeficientes_calibracion.json"
)

ESTRUCTURAS = {
    "M1_lineal_adc": {
        "espacio": "T",
        "ecuacion": "T = θ0 + θ1·u,  u = x/4095",
        "num_parametros": 2,
    },
    "M2_beta": {
        "espacio": "inv_T",
        "ecuacion": "1/T_K = θ0 + θ1·L,  L = ln(x/(4095−x))",
        "num_parametros": 2,
    },
    "M3_steinhart_hart": {
        "espacio": "inv_T",
        "ecuacion": "1/T_K = θ0 + θ1·L + θ2·L² + θ3·L³",
        "num_parametros": 4,
    },
}


def variable_L(adc):
    adc = np.asarray(adc, dtype=float)
    return np.log(adc / (ms.ADC_MAX - adc))


def matriz_diseno(adc, estructura):
    """
    Matriz de diseño X (n × p): una fila por punto, una columna por parámetro.

        M1:  X = [1, u]
        M2:  X = [1, L]
        M3:  X = [1, L, L², L³]
    """
    adc = np.asarray(adc, dtype=float)

    if estructura == "M1_lineal_adc":
        u = adc / ms.ADC_MAX
        return np.column_stack([np.ones_like(u), u])

    L = variable_L(adc)
    if estructura == "M2_beta":
        return np.column_stack([np.ones_like(L), L])
    if estructura == "M3_steinhart_hart":
        return np.column_stack([np.ones_like(L), L, L ** 2, L ** 3])
    raise ValueError(f"Estructura desconocida: {estructura}")


def objetivo(temperatura_c, estructura):
    """Variable de respuesta y del ajuste: T en °C o 1/T en 1/K."""
    temperatura_c = np.asarray(temperatura_c, dtype=float)
    if ESTRUCTURAS[estructura]["espacio"] == "T":
        return temperatura_c
    return 1.0 / (temperatura_c + 273.15)


def respuesta_a_temperatura(y, estructura):
    """Convierte la salida del modelo (T o 1/T) a °C."""
    y = np.asarray(y, dtype=float)
    if ESTRUCTURAS[estructura]["espacio"] == "T":
        return y
    return 1.0 / y - 273.15


def predecir(adc, estructura, theta):
    """Temperatura [°C] predicha por la estructura con coeficientes theta."""
    return respuesta_a_temperatura(matriz_diseno(adc, estructura) @ np.asarray(theta), estructura)


# ==========================================
# USO DE LOS COEFICIENTES DE E1
# ==========================================


def cargar_coeficientes(ruta=RUTA_COEFICIENTES):
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecute primero E1_calibracion/calibracion.py"
        )
    return json.loads(ruta.read_text(encoding="utf-8"))


def adc_a_temperatura_calibrada(adc, canal, coeficientes):
    """
    Temperatura CALIBRADA [°C] del canal (1, 2 o 3) a partir de la cuenta ADC.
    Devuelve NaN en las lecturas de los extremos (sensor en corto o desconectado).
    """
    adc = np.asarray(adc, dtype=float)
    validas = (adc > ms.ADC_LIMITE_INFERIOR) & (adc < ms.ADC_LIMITE_SUPERIOR)
    adc_seguro = np.where(validas, adc, 2048.0)

    estructura = coeficientes["estructura"]
    theta = coeficientes["canales"][str(canal)]["theta"]
    temperatura = predecir(adc_seguro, estructura, theta)
    return np.where(validas, temperatura, np.nan)
