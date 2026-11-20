
import numpy as np
import pandas as pd

from datetime import datetime, timedelta

# ==========================================
# CONFIGURACION DE LA SIMULACION
# ==========================================

DURACION_HORAS = 24
INTERVALO_MINUTOS = 1

NUM_SENSORES = 3

TEMP_INICIAL = 5.0
TEMP_MIN = 2.0
TEMP_MAX = 8.0

# Semilla para obtener siempre los mismos datos
rng = np.random.default_rng(42)

# Diferencias de medicion entre sensores
DESVIACIONES = [0.0, 0.15, -0.20]

# Fecha ficticia de inicio
INICIO = datetime(2026, 1, 1)

# ==========================================
# EVENTOS SIMULADOS
# ==========================================

# Intervalos expresados en minutos desde el inicio
APERTURAS_TAPA = [
    (9 * 60, 9 * 60 + 12),
    (13 * 60 + 30, 13 * 60 + 40),
    (18 * 60, 18 * 60 + 8)
]

# Desconexion del sensor 3
FALLA_SENSOR_3 = (19 * 60, 19 * 60 + 10)


def tapa_abierta(minuto):
    return any(
        inicio <= minuto < fin
        for inicio, fin in APERTURAS_TAPA
    )


# ==========================================
# GENERACION DE TEMPERATURAS
# ==========================================

datos = []

temperaturas_reales = [
    TEMP_INICIAL,
    TEMP_INICIAL,
    TEMP_INICIAL
]

total_minutos = DURACION_HORAS * 60

for minuto in range(total_minutos):

    abierta = tapa_abierta(minuto)

    # Temperatura ambiental variable durante el dia
    temperatura_ambiente = (
        25 + 3 * np.sin(2 * np.pi * minuto / 1440)
    )

    for sensor in range(NUM_SENSORES):

        # La caja se calienta lentamente cuando esta cerrada
        # y mas rapidamente cuando se abre la tapa.
        coeficiente = 0.035 if abierta else 0.0005

        temperaturas_reales[sensor] += (
            coeficiente *
            (temperatura_ambiente - temperaturas_reales[sensor])
        )

        # Ruido aleatorio pequeño de medicion
        ruido = rng.normal(0, 0.08)

        temperatura_medida = (
            temperaturas_reales[sensor]
            + DESVIACIONES[sensor]
            + ruido
        )

        # Detectar desconexion del sensor 3
        desconectado = (
            sensor == 2
            and FALLA_SENSOR_3[0] <= minuto < FALLA_SENSOR_3[1]
        )

        if desconectado:
            temperatura_medida = np.nan
            estado_sensor = "DESCONECTADO"
            estado = "ERROR"

        else:
            estado_sensor = "OK"

            if (
                temperatura_medida < TEMP_MIN
                or temperatura_medida > TEMP_MAX
            ):
                estado = "ALARMA"
            else:
                estado = "NORMAL"

        # Registrar la medicion
        datos.append({
            "FechaHora": INICIO + timedelta(minutes=minuto),
            "Tiempo_min": minuto,
            "Sensor": sensor + 1,
            "Temperatura_C": temperatura_medida,
            "Tapa_abierta": abierta,
            "Estado_sensor": estado_sensor,
            "Estado": estado,
            "Origen": "SINTETICO"
        })


# ==========================================
# GUARDAR ARCHIVO CSV
# ==========================================

df = pd.DataFrame(datos)

archivo = "datos_sinteticos_cadena_frio.csv"

df.to_csv(archivo, index=False)

print("Simulacion finalizada.")
print(f"Archivo generado: {archivo}")

print("\nPrimeras mediciones:")
print(df.head(9))

print("\nDistribucion de estados:")
print(df["Estado"].value_counts())

print("\nCantidad de registros:")
print(len(df))
