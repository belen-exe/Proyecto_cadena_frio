"""
Simulador del Experimento E3 (R11): datos de operación normal y eventos.

TODOS LOS DATOS QUE GENERA ESTE SCRIPT SON SIMULADOS (Origen = "SIMULADO").

Escenario
---------
La caja aislada, con la carga, está dentro de la nevera (aire ≈ 4–5 °C con una
oscilación pequeña por el ciclo del compresor). Al abrir la tapa, el aire interior
queda expuesto al aire de la cocina (~25 °C). Cada sensor responde a un ritmo
distinto según su posición (factor por sensor).

Modelo térmico (ley de enfriamiento de Newton, solución EXACTA por paso)
----------------------------------------------------------------------
    T(t + Ts) = T_dest + (T(t) − T_dest) · exp(−Ts / τ)

  * Contenido de la caja: tiende al aire de la nevera con τ = TAU_CERRADA.
  * Aire junto al sensor i:
      - tapa abierta  -> tiende al aire de la cocina con τ_i = TAU_ABIERTA / factor_i
      - tapa cerrada  -> vuelve a la temperatura del contenido con τ = TAU_RECUPERACION
  * Término común: la oscilación del aire de la nevera (ciclo del compresor) se
    cuela por las paredes y la tapa y llega a los TRES sensores a la vez:
        común(t) = GANANCIA_COMUN · (T_nevera(t) − NEVERA_MEDIA_C)
    Es lo que hace que los sensores estén correlacionados en operación normal
    (la estructura que después aprovecha el PCA).
  * Medición del sensor i = aire_i + común + desfase_i + ruido gaussiano (°C),
    que luego pasa por comun/modelo_sensor.py para obtener la cuenta ADC.
  * Desconexión de un sensor: el ADC marca ≈ 4095 (no NaN).

Archivos generados en E3_eventos/datos/
---------------------------------------
  entrenamiento.csv      30 min de operación normal
  validacion.csv         20 min de operación normal (independiente)
  prueba.csv             ≥ 4 aperturas de 30 s y ≥ 2 desconexiones
  tabla_eventos.csv      instante real de inicio y fin de cada evento de prueba
  VERDAD_NO_USAR.json    parámetros y temperaturas reales. EL ANÁLISIS NO LO LEE.

Uso:  python simulador_E3.py   (desde cualquier carpeta)
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Permite importar comun/ sin instalar nada.
RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

CARPETA_DATOS = Path(__file__).resolve().parent / "datos"

ORIGEN = "SIMULADO"

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

# Periodo de muestreo [s]. Configurable; el firmware usa el mismo valor (1000 ms).
TS_S = 1.0

NUM_SENSORES = ms.NUM_SENSORES

# Temperatura inicial del interior de la caja [°C].
TEMP_INICIAL = 5.0

# Constantes de tiempo térmicas [min].
# TAU_CERRADA: la misma caja de E2. Se usa el τ identificado en R9 (PSO: 221,4 min;
# regresión: 220,7 min) para que E2 y E3 describan el mismo contenedor.
TAU_CERRADA = 221.0
TAU_ABIERTA = 28.07   # valor del modelo original, sin cambios

# Constante de tiempo con la que el aire junto al sensor vuelve a la temperatura
# del contenido después de cerrar la tapa [min].
# SUPUESTO NUEVO de este simulador: sin él, el calentamiento de cada apertura no
# se recuperaría (el contenido cambia con τ = 221 min) y los eventos se acumularían.
TAU_RECUPERACION = 2.0

# Desfase fijo de cada sensor por su posición dentro de la caja [°C] (sin cambios).
DESVIACIONES = [0.0, 0.15, -0.20]

# Ruido de la temperatura en el punto de medición [°C] (sin cambios).
RUIDO_TEMPERATURA_C = 0.08

# Fracción de la oscilación del aire de la nevera que llega a los tres sensores
# por igual (término común). SUPUESTO: 0,6 · 0,5 °C = ±0,3 °C, bastante mayor que
# el ruido (0,08 °C), así que en operación normal los 3 canales suben y bajan juntos.
GANANCIA_COMUN = 0.6

# Factor de respuesta de cada sensor durante una apertura (1 = el más expuesto).
# Sensor 1: junto a la tapa; sensor 2: a media altura; sensor 3: al fondo.
FACTOR_RESPUESTA_APERTURA = [1.0, 0.6, 0.35]

# Aire de la nevera [°C]: media + oscilación senoidal del ciclo del compresor.
NEVERA_MEDIA_C = 4.5
NEVERA_AMPLITUD_C = 0.5
NEVERA_PERIODO_MIN = 30.0

# Semillas de cada sesión (la de entrenamiento es la semilla original, 42).
SEMILLAS = {
    "entrenamiento": 42,
    "validacion": 43,
    "prueba": 44,
}

# Duración [s] y hora del día de inicio [h] de cada sesión.
DURACION_S = {
    "entrenamiento": 30 * 60,
    "validacion": 20 * 60,
    "prueba": 70 * 60,
}

HORA_INICIO_H = {
    "entrenamiento": 9.0,
    "validacion": 11.0,
    "prueba": 14.0,
}

# Eventos de la sesión de prueba: (tipo, sensor, t_inicio_s, t_fin_s).
# Separados 10 min (5 · TAU_RECUPERACION) para que el sistema se recupere,
# sin solaparse, y con 10 min iniciales de operación normal.
EVENTOS_PRUEBA = [
    ("apertura", None, 600, 630),
    ("desconexion", 3, 1200, 1260),
    ("apertura", None, 1800, 1830),
    ("apertura", None, 2400, 2430),
    ("desconexion", 1, 3000, 3060),
    ("apertura", None, 3600, 3630),
]

# ==========================================
# 2. MODELOS DE TEMPERATURA AMBIENTE
# ==========================================


def temperatura_cocina(minuto_del_dia):
    """Aire de la cocina [°C]: el mismo modelo diario del simulador original."""
    return 25 + 3 * np.sin(2 * np.pi * minuto_del_dia / 1440)


def temperatura_nevera(minuto, fase_rad):
    """Aire de la nevera [°C] con la oscilación del compresor."""
    return NEVERA_MEDIA_C + NEVERA_AMPLITUD_C * np.sin(
        2 * np.pi * minuto / NEVERA_PERIODO_MIN + fase_rad
    )


# ==========================================
# 3. MODELO TÉRMICO DE PRIMER ORDEN (Newton, solución exacta)
# ==========================================


def actualizar_temperatura(temperatura_actual, temperatura_destino, tau, intervalo):
    """Un paso exacto de la ley de Newton. tau e intervalo en las mismas unidades."""
    return (
        temperatura_destino
        + (temperatura_actual - temperatura_destino) * np.exp(-intervalo / tau)
    )


# ==========================================
# 4. SIMULACIÓN DE UNA SESIÓN
# ==========================================


def simular_sesion(nombre, eventos):
    """
    Simula una sesión completa.

    Devuelve (tabla_csv, verdad), donde tabla_csv solo contiene lo que vería el
    sistema real (tiempo y cuentas ADC) y verdad contiene las temperaturas reales.
    """
    rng = np.random.default_rng(SEMILLAS[nombre])

    num_muestras = int(round(DURACION_S[nombre] / TS_S))
    t_s = np.arange(num_muestras) * TS_S

    intervalo_min = TS_S / 60.0
    minuto_inicio_dia = HORA_INICIO_H[nombre] * 60
    fase_nevera = rng.uniform(0, 2 * np.pi)

    factores = np.array(FACTOR_RESPUESTA_APERTURA)
    desviaciones = np.array(DESVIACIONES)

    # Estados reales
    temp_contenido = TEMP_INICIAL
    temp_aire = np.full(NUM_SENSORES, TEMP_INICIAL)

    # Historias
    hist_contenido = np.empty(num_muestras)
    hist_aire = np.empty((num_muestras, NUM_SENSORES))
    hist_medida = np.empty((num_muestras, NUM_SENSORES))
    hist_nevera = np.empty(num_muestras)
    hist_cocina = np.empty(num_muestras)
    hist_comun = np.empty(num_muestras)
    desconectado = np.zeros((num_muestras, NUM_SENSORES), dtype=bool)
    tapa_abierta = np.zeros(num_muestras, dtype=bool)

    for k, t in enumerate(t_s):
        minuto = t / 60.0

        # Estado de los eventos en este instante
        for tipo, sensor, inicio, fin in eventos:
            if inicio <= t < fin:
                if tipo == "apertura":
                    tapa_abierta[k] = True
                elif tipo == "desconexion":
                    desconectado[k, sensor - 1] = True

        aire_nevera = temperatura_nevera(minuto, fase_nevera)
        aire_cocina = temperatura_cocina(minuto_inicio_dia + minuto)

        # Registrar el estado actual (la muestra k se toma en el instante t)
        hist_contenido[k] = temp_contenido
        hist_aire[k] = temp_aire
        hist_nevera[k] = aire_nevera
        hist_cocina[k] = aire_cocina

        ruido = rng.normal(0, RUIDO_TEMPERATURA_C, size=NUM_SENSORES)
        comun = GANANCIA_COMUN * (aire_nevera - NEVERA_MEDIA_C)   # igual para los 3
        hist_comun[k] = comun
        hist_medida[k] = temp_aire + comun + desviaciones + ruido

        # Avanzar un paso Ts
        if tapa_abierta[k]:
            temp_aire = actualizar_temperatura(
                temp_aire, aire_cocina, TAU_ABIERTA / factores, intervalo_min
            )
        else:
            temp_aire = actualizar_temperatura(
                temp_aire, temp_contenido, TAU_RECUPERACION, intervalo_min
            )

        temp_contenido = actualizar_temperatura(
            temp_contenido, aire_nevera, TAU_CERRADA, intervalo_min
        )

    # Paso por el canal de medición: temperatura -> ADC (comun/modelo_sensor.py)
    adc = np.empty((num_muestras, NUM_SENSORES), dtype=int)
    for i, sensor in enumerate(ms.SENSORES):
        adc[:, i] = ms.temperatura_a_adc(
            hist_medida[:, i], sensor, rng=rng, desconectado=desconectado[:, i]
        )

    tabla = pd.DataFrame({"t_s": np.round(t_s, 3)})
    for i in range(NUM_SENSORES):
        tabla[f"adc_{i + 1}"] = adc[:, i]
    tabla["Origen"] = ORIGEN

    verdad = {
        "semilla": SEMILLAS[nombre],
        "duracion_s": DURACION_S[nombre],
        "hora_inicio_h": HORA_INICIO_H[nombre],
        "fase_nevera_rad": fase_nevera,
        "t_s": t_s.tolist(),
        "T_nevera_C": np.round(hist_nevera, 4).tolist(),
        "T_cocina_C": np.round(hist_cocina, 4).tolist(),
        "T_contenido_C": np.round(hist_contenido, 4).tolist(),
        "termino_comun_C": np.round(hist_comun, 4).tolist(),
        "tapa_abierta": tapa_abierta.astype(int).tolist(),
    }
    for i in range(NUM_SENSORES):
        # Temperatura real en el punto de medición (aire + común + desfase), sin ruido.
        verdad[f"T_real_sensor_{i + 1}_C"] = np.round(
            hist_aire[:, i] + hist_comun + desviaciones[i], 4
        ).tolist()
        verdad[f"desconectado_sensor_{i + 1}"] = desconectado[:, i].astype(int).tolist()

    return tabla, verdad


# ==========================================
# 5. ESCRITURA DE ARCHIVOS
# ==========================================


def json_legible(objeto):
    """JSON con sangría, pero con cada lista numérica en una sola línea."""
    texto = json.dumps(objeto, indent=2, ensure_ascii=False)
    return re.sub(
        r"\[\s*([^\[\]{}\"]*?)\s*\]",
        lambda m: "[" + " ".join(m.group(1).split()) + "]",
        texto,
    )


def main():
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    sesiones = {
        "entrenamiento": [],
        "validacion": [],
        "prueba": EVENTOS_PRUEBA,
    }

    verdad_total = {
        "ADVERTENCIA": (
            "Datos verdaderos de la simulación. Solo sirven para verificar al "
            "final. Ningún análisis, ajuste ni elección de umbral debe leer este archivo."
        ),
        "Origen": ORIGEN,
        "parametros_modelo": {
            "TS_S": TS_S,
            "TEMP_INICIAL_C": TEMP_INICIAL,
            "TAU_CERRADA_min": TAU_CERRADA,
            "TAU_ABIERTA_min": TAU_ABIERTA,
            "TAU_RECUPERACION_min": TAU_RECUPERACION,
            "DESVIACIONES_C": DESVIACIONES,
            "RUIDO_TEMPERATURA_C": RUIDO_TEMPERATURA_C,
            "GANANCIA_COMUN": GANANCIA_COMUN,
            "FACTOR_RESPUESTA_APERTURA": FACTOR_RESPUESTA_APERTURA,
            "NEVERA_MEDIA_C": NEVERA_MEDIA_C,
            "NEVERA_AMPLITUD_C": NEVERA_AMPLITUD_C,
            "NEVERA_PERIODO_MIN": NEVERA_PERIODO_MIN,
            "COCINA": "25 + 3·sin(2π·minuto_del_dia/1440) °C",
        },
        "parametros_sensores": {
            "semilla_sensores": ms.SEMILLA_SENSORES,
            "ruido_adc_cuentas": ms.RUIDO_ADC_CUENTAS,
            "vcc_v": ms.VCC_V,
            "sensores": [s.como_dict() for s in ms.SENSORES],
        },
        "semillas_sesiones": SEMILLAS,
        "sesiones": {},
    }

    for nombre, eventos in sesiones.items():
        tabla, verdad = simular_sesion(nombre, eventos)

        ruta = CARPETA_DATOS / f"{nombre}.csv"
        tabla.to_csv(ruta, index=False)
        verdad_total["sesiones"][nombre] = verdad

        print(f"Generado: {ruta.relative_to(RAIZ_REPO)}  ({len(tabla)} filas)")

    # Tabla de eventos de la sesión de prueba
    tabla_eventos = pd.DataFrame(
        EVENTOS_PRUEBA, columns=["tipo", "sensor", "t_inicio_s", "t_fin_s"]
    )
    tabla_eventos["sensor"] = tabla_eventos["sensor"].astype("Int64")
    tabla_eventos["Origen"] = ORIGEN
    ruta_eventos = CARPETA_DATOS / "tabla_eventos.csv"
    tabla_eventos.to_csv(ruta_eventos, index=False)
    print(f"Generado: {ruta_eventos.relative_to(RAIZ_REPO)}  ({len(tabla_eventos)} eventos)")

    ruta_verdad = CARPETA_DATOS / "VERDAD_NO_USAR.json"
    ruta_verdad.write_text(json_legible(verdad_total), encoding="utf-8")
    print(f"Generado: {ruta_verdad.relative_to(RAIZ_REPO)}  (no lo lea el análisis)")


if __name__ == "__main__":
    main()
