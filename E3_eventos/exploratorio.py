
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==========================================
# CONFIGURACION
# ==========================================

ARCHIVO = "datos_sinteticos_cadena_frio.csv"

TEMP_MIN = 2.0
TEMP_MAX = 8.0

# ==========================================
# CARGAR DATOS
# ==========================================

df = pd.read_csv(ARCHIVO)

df["FechaHora"] = pd.to_datetime(df["FechaHora"])

print("\n========== INFORMACION GENERAL ==========")

print(f"Total de registros: {len(df)}")
print(f"Sensores encontrados: {df['Sensor'].nunique()}")
print(f"Periodo: {df['FechaHora'].min()} - {df['FechaHora'].max()}")

print("\nValores faltantes:")
print(df.isnull().sum())

# ==========================================
# ESTADISTICAS POR SENSOR
# ==========================================

print("\n========== ESTADISTICAS POR SENSOR ==========")

estadisticas = df.groupby("Sensor")["Temperatura_C"].agg(
    ["mean", "min", "max", "std"]
)

estadisticas.columns = [
    "Promedio_C",
    "Minimo_C",
    "Maximo_C",
    "Desviacion_C"
]

print(estadisticas.round(2))

# ==========================================
# DISTRIBUCION DE ESTADOS
# ==========================================

print("\n========== ESTADOS DEL SISTEMA ==========")

print(df["Estado"].value_counts())

print("\nPorcentaje de cada estado:")
print(
    (df["Estado"].value_counts(normalize=True) * 100).round(2)
)

# ==========================================
# ANALISIS DE ALARMAS
# ==========================================

alarmas = df[df["Estado"] == "ALARMA"]

print("\n========== ANALISIS DE ALARMAS ==========")

print(f"Total de alarmas: {len(alarmas)}")

if not alarmas.empty:

    print("\nPrimeras alarmas detectadas:")

    print(
        alarmas[
            ["FechaHora", "Sensor", "Temperatura_C"]
        ].head(10)
    )

    print("\nAlarmas por sensor:")
    print(alarmas.groupby("Sensor").size())

# ==========================================
# ANALISIS DE FALLAS
# ==========================================

fallas = df[df["Estado_sensor"] != "OK"]

print("\n========== FALLAS DE SENSORES ==========")

print(f"Total de registros con fallas: {len(fallas)}")

print(fallas.groupby("Sensor").size())

# ==========================================
# GRAFICA 1: TEMPERATURA EN EL TIEMPO
# ==========================================

fig, ax = plt.subplots(figsize=(14, 6))

for sensor in sorted(df["Sensor"].unique()):

    datos = df[df["Sensor"] == sensor]

    ax.plot(
        datos["FechaHora"],
        datos["Temperatura_C"],
        label=f"Sensor {sensor}",
        linewidth=1
    )

# Zona permitida
ax.axhspan(
    TEMP_MIN,
    TEMP_MAX,
    alpha=0.15,
    label="Rango permitido (2-8 °C)"
)

# Limites
ax.axhline(TEMP_MIN, linestyle="--", linewidth=1)
ax.axhline(TEMP_MAX, linestyle="--", linewidth=1)

# Marcar intervalos de apertura
aperturas = df[df["Tapa_abierta"]].groupby(
    "Tiempo_min"
).size()

if not aperturas.empty:

    minutos_apertura = aperturas.index

    for minuto in minutos_apertura:

        inicio = df.loc[
            df["Tiempo_min"] == minuto,
            "FechaHora"
        ].iloc[0]

        ax.axvspan(
            inicio,
            inicio + pd.Timedelta(minutes=1),
            color="orange",
            alpha=0.08
        )

ax.set_title("Evolucion de temperatura de la cadena de frio")
ax.set_xlabel("Tiempo")
ax.set_ylabel("Temperatura (°C)")

ax.xaxis.set_major_formatter(
    mdates.DateFormatter("%H:%M")
)

ax.legend()
ax.grid(True)
fig.autofmt_xdate()
plt.tight_layout()
plt.show()

# ==========================================
# GRAFICA 2: DISTRIBUCION DE ESTADOS
# ==========================================

conteo_estados = df["Estado"].value_counts()

plt.figure(figsize=(8, 5))

conteo_estados.plot(
    kind="bar",
    rot=0
)

plt.title("Cantidad de registros por estado")
plt.xlabel("Estado")
plt.ylabel("Cantidad de registros")
plt.grid(axis="y")
plt.tight_layout()
plt.show()

# ==========================================
# GRAFICA 3: DISTRIBUCION DE TEMPERATURAS
# ==========================================

plt.figure(figsize=(9, 5))

for sensor in sorted(df["Sensor"].unique()):

    datos = df[df["Sensor"] == sensor]

    plt.hist(
        datos["Temperatura_C"].dropna(),
        bins=35,
        alpha=0.45,
        label=f"Sensor {sensor}"
    )

plt.axvline(TEMP_MIN, linestyle="--", label="Mínimo permitido")
plt.axvline(TEMP_MAX, linestyle="--", label="Máximo permitido")

plt.title("Distribucion de temperaturas por sensor")
plt.xlabel("Temperatura (°C)")
plt.ylabel("Frecuencia")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()

print("\nAnalisis finalizado.")
