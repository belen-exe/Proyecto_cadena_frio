
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURACION
# ==========================================

DURACION_HORAS = 24
INTERVALO_MINUTOS = 1

NUM_SENSORES = 3

TEMP_INICIAL = 5.0
TEMP_MIN = 2.0
TEMP_MAX = 8.0

# Constantes de tiempo termicas (minutos)
TAU_CERRADA = 2000.0
TAU_ABIERTA = 28.07

# Diferencias artificiales entre sensores
DESVIACIONES = [0.0, 0.15, -0.20]

# Ruido sintetico
rng = np.random.default_rng(42)

INICIO = datetime(2026, 1, 1)

# ==========================================
# 2. EVENTOS DE APERTURA
# ==========================================

APERTURAS = [
    (9 * 60, 9 * 60 + 12),
    (13 * 60 + 30, 13 * 60 + 40),
    (18 * 60, 18 * 60 + 8)
]

FALLA_SENSOR_3 = (19 * 60, 19 * 60 + 10)


def tapa_abierta(minuto):
    return any(
        inicio <= minuto < fin
        for inicio, fin in APERTURAS
    )


# ==========================================
# 3. MODELO DE TEMPERATURA AMBIENTAL
# ==========================================

def temperatura_ambiente(minuto):

    return (
        25 + 3 * np.sin(2 * np.pi * minuto / 1440)
    )


# ==========================================
# 4. MODELO TERMICO DE PRIMER ORDEN
# ==========================================

def actualizar_temperatura(
    temperatura_actual,
    temperatura_ambiente,
    tau,
    intervalo
):

    temperatura_nueva = (
        temperatura_ambiente
        + (temperatura_actual - temperatura_ambiente)
        * np.exp(-intervalo / tau)
    )

    return temperatura_nueva


# ==========================================
# 5. SIMULACION
# ==========================================

temperaturas = [TEMP_INICIAL] * NUM_SENSORES

datos = []

total_minutos = DURACION_HORAS * 60

for minuto in range(total_minutos):

    abierta = tapa_abierta(minuto)

    ambiente = temperatura_ambiente(minuto)

    tau = TAU_ABIERTA if abierta else TAU_CERRADA

    for sensor in range(NUM_SENSORES):

        # Actualizar la temperatura real
        temperaturas[sensor] = actualizar_temperatura(
            temperaturas[sensor],
            ambiente,
            tau,
            INTERVALO_MINUTOS
        )

        # Agregar diferencias y ruido
        ruido = rng.normal(0, 0.08)

        temperatura_medida = (
            temperaturas[sensor]
            + DESVIACIONES[sensor]
            + ruido
        )

        # Simular desconexion del sensor 3
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

        datos.append({
            "FechaHora": INICIO + timedelta(minutes=minuto),
            "Tiempo_min": minuto,
            "Sensor": sensor + 1,
            "Temperatura_C": temperatura_medida,
            "Temperatura_ambiente_C": ambiente,
            "Tapa_abierta": abierta,
            "Estado_sensor": estado_sensor,
            "Estado": estado,
            "Origen": "SINTETICO_MODELO_TERMICO"
        })


# ==========================================
# 6. CREAR DATAFRAME
# ==========================================

df = pd.DataFrame(datos)

df.to_csv(
    "datos_modelo_termico.csv",
    index=False
)

print("Simulacion termica finalizada.")

print(f"Registros generados: {len(df)}")

# ==========================================
# 7. RESUMEN ESTADISTICO
# ==========================================

print("\nESTADISTICAS POR SENSOR")

estadisticas = df.groupby("Sensor")["Temperatura_C"].agg(
    ["mean", "min", "max", "std"]
)

print(estadisticas.round(2))

print("\nESTADOS DEL SISTEMA")

print(df["Estado"].value_counts())


# ==========================================
# 8. TIEMPO FUERA DEL RANGO
# ==========================================

print("\nTIEMPO FUERA DEL RANGO PERMITIDO")

for sensor in range(1, NUM_SENSORES + 1):

    datos_sensor = df[df["Sensor"] == sensor]

    fuera_rango = datos_sensor[
        datos_sensor["Temperatura_C"].notna()
        & (
            (datos_sensor["Temperatura_C"] < TEMP_MIN)
            | (datos_sensor["Temperatura_C"] > TEMP_MAX)
        )
    ]

    print(
        f"Sensor {sensor}: "
        f"{len(fuera_rango)} minutos fuera del rango"
    )


# ==========================================
# 9. GRAFICA DE TEMPERATURA
# ==========================================

fig, ax = plt.subplots(figsize=(14, 6))

for sensor in range(1, NUM_SENSORES + 1):

    datos_sensor = df[df["Sensor"] == sensor]

    ax.plot(
        datos_sensor["Tiempo_min"] / 60,
        datos_sensor["Temperatura_C"],
        label=f"Sensor {sensor}",
        linewidth=1
    )

# Temperatura ambiente
ambiente = df.drop_duplicates("Tiempo_min")

ax.plot(
    ambiente["Tiempo_min"] / 60,
    ambiente["Temperatura_ambiente_C"],
    linestyle=":",
    label="Temperatura ambiente"
)

# Rango permitido
ax.axhspan(
    TEMP_MIN,
    TEMP_MAX,
    alpha=0.15,
    label="Rango permitido"
)

ax.axhline(TEMP_MIN, linestyle="--")
ax.axhline(TEMP_MAX, linestyle="--")

# Marcar aperturas
for inicio, fin in APERTURAS:

    ax.axvspan(
        inicio / 60,
        fin / 60,
        alpha=0.2
    )

ax.set_title("Modelo termico de la cadena de frio")
ax.set_xlabel("Tiempo (horas)")
ax.set_ylabel("Temperatura (°C)")

ax.legend()
ax.grid()
plt.tight_layout()
plt.show()
