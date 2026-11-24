"""
Análisis exploratorio de los datos del Experimento E3 (datos SIMULADOS).

Lee (de E3_eventos/datos/):
  entrenamiento.csv, validacion.csv, prueba.csv  -> t_s, adc_1, adc_2, adc_3, Origen
  tabla_eventos.csv                              -> tipo, sensor, t_inicio_s, t_fin_s, Origen

NO lee VERDAD_NO_USAR.json.

Este script solo describe los datos: no elige componentes, umbrales ni ningún
parámetro del detector (eso será R12, y solo con datos de entrenamiento).

Las temperaturas en °C se obtienen con la conversión β NOMINAL de
comun/modelo_sensor.py: es una CONVERSIÓN PROVISIONAL, SIN CALIBRAR.

Genera en E3_eventos/resultados/:
  exploratorio_entrenamiento.png, exploratorio_validacion.png,
  exploratorio_prueba.png, exploratorio_histograma.png

Uso:  python exploratorio.py   (desde cualquier carpeta)
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Permite importar comun/ sin instalar nada.
RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA = Path(__file__).resolve().parent
CARPETA_DATOS = CARPETA / "datos"
CARPETA_RESULTADOS = CARPETA / "resultados"

SESIONES = ["entrenamiento", "validacion", "prueba"]

TEMP_MIN = 2.0
TEMP_MAX = 8.0

# Lecturas en los extremos del ADC (mismos límites que el firmware).
ADC_LIMITE_INFERIOR = ms.ADC_LIMITE_INFERIOR
ADC_LIMITE_SUPERIOR = ms.ADC_LIMITE_SUPERIOR

# Mostrar las ventanas de las gráficas además de guardarlas.
MOSTRAR_GRAFICAS = True

ETIQUETA_CONVERSION = "conversión provisional, sin calibrar"

COLORES_EVENTO = {
    "apertura": "tab:orange",
    "desconexion": "tab:red",
}

# ==========================================
# CARGAR DATOS
# ==========================================


def cargar_sesion(nombre):
    df = pd.read_csv(CARPETA_DATOS / f"{nombre}.csv")
    canales_adc = [c for c in df.columns if c.startswith("adc_")]
    return df, canales_adc


datos = {}
for nombre in SESIONES:
    datos[nombre] = cargar_sesion(nombre)

eventos = pd.read_csv(CARPETA_DATOS / "tabla_eventos.csv")

# ==========================================
# INFORMACIÓN GENERAL Y PÉRDIDA DE MUESTRAS
# ==========================================

print("\n========== INFORMACIÓN GENERAL (datos SIMULADOS) ==========")

for nombre, (df, canales_adc) in datos.items():
    t = df["t_s"].to_numpy()
    ts = float(np.median(np.diff(t)))
    duracion = t[-1] - t[0] + ts
    esperadas = int(round(duracion / ts))
    perdida = 100 * (esperadas - len(df)) / esperadas

    print(f"\n[{nombre}]")
    print(f"  Registros: {len(df)}   Canales: {len(canales_adc)}")
    print(f"  Duración: {duracion / 60:.1f} min   Ts (mediana): {ts:.3f} s")
    print(f"  Muestras esperadas: {esperadas}   Pérdida de muestras: {perdida:.2f} %")
    print(f"  Origen: {', '.join(df['Origen'].unique())}")
    print(f"  Valores faltantes: {int(df.isnull().sum().sum())}")

# ==========================================
# ESTADÍSTICAS POR SENSOR (ADC y °C provisional)
# ==========================================

print("\n========== ESTADÍSTICAS POR SENSOR ==========")

for nombre, (df, canales_adc) in datos.items():
    print(f"\n[{nombre}] cuentas ADC")
    print(df[canales_adc].agg(["mean", "min", "max", "std"]).T.round(2))

    temperaturas = pd.DataFrame({
        c.replace("adc_", "T_"): ms.adc_a_temperatura_beta(df[c]) for c in canales_adc
    })
    print(f"[{nombre}] °C ({ETIQUETA_CONVERSION})")
    print(temperaturas.agg(["mean", "min", "max", "std"]).T.round(3))

    extremos = (
        (df[canales_adc] <= ADC_LIMITE_INFERIOR) | (df[canales_adc] >= ADC_LIMITE_SUPERIOR)
    ).sum()
    print(f"[{nombre}] lecturas en los extremos del ADC (posible desconexión):")
    print(extremos.to_string())

# ==========================================
# EVENTOS REGISTRADOS (sesión de prueba)
# ==========================================

print("\n========== EVENTOS REGISTRADOS (prueba) ==========")
print(eventos.to_string(index=False))

# ==========================================
# GRÁFICAS
# ==========================================

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)


def marcar_eventos(ax, tabla_eventos):
    """Sombrea cada evento de la tabla; una sola entrada de leyenda por tipo."""
    tipos_rotulados = set()
    for _, ev in tabla_eventos.iterrows():
        tipo = ev["tipo"]
        etiqueta = None
        if tipo not in tipos_rotulados:
            etiqueta = "Apertura de tapa" if tipo == "apertura" else "Desconexión de sensor"
            tipos_rotulados.add(tipo)
        ax.axvspan(
            ev["t_inicio_s"] / 60,
            ev["t_fin_s"] / 60,
            color=COLORES_EVENTO.get(tipo, "gray"),
            alpha=0.25,
            label=etiqueta,
        )


# Gráfica 1: ADC y temperatura provisional en el tiempo, una figura por sesión
for nombre, (df, canales_adc) in datos.items():
    fig, (ax_adc, ax_t) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    minutos = df["t_s"] / 60

    for c in canales_adc:
        sensor = c.replace("adc_", "")
        ax_adc.plot(minutos, df[c], linewidth=0.8, label=f"Sensor {sensor}")
        ax_t.plot(
            minutos, ms.adc_a_temperatura_beta(df[c]), linewidth=0.8, label=f"Sensor {sensor}"
        )

    if nombre == "prueba":
        marcar_eventos(ax_adc, eventos)
        marcar_eventos(ax_t, eventos)

    ax_t.axhspan(TEMP_MIN, TEMP_MAX, color="tab:green", alpha=0.08, label="Rango permitido (2-8 °C)")

    ax_adc.set_title(f"E3 - sesión de {nombre} - datos SIMULADOS")
    ax_adc.set_ylabel("Cuenta ADC (0-4095)")
    ax_adc.legend(loc="upper right", fontsize=8)
    ax_adc.grid(True)

    ax_t.set_title(f"Temperatura ({ETIQUETA_CONVERSION}) - SIMULADO")
    ax_t.set_xlabel("Tiempo (min)")
    ax_t.set_ylabel("Temperatura (°C)")
    ax_t.legend(loc="upper right", fontsize=8)
    ax_t.grid(True)

    fig.tight_layout()
    ruta = CARPETA_RESULTADOS / f"exploratorio_{nombre}.png"
    fig.savefig(ruta, dpi=120)
    print(f"Gráfica guardada: {ruta.relative_to(RAIZ_REPO)}")

# Gráfica 2: distribución de temperaturas en operación normal (entrenamiento)
df, canales_adc = datos["entrenamiento"]
fig, ax = plt.subplots(figsize=(9, 5))

for c in canales_adc:
    ax.hist(
        ms.adc_a_temperatura_beta(df[c]),
        bins=35,
        alpha=0.45,
        label=f"Sensor {c.replace('adc_', '')}",
    )

ax.set_title(f"Distribución de temperaturas - entrenamiento - SIMULADO\n({ETIQUETA_CONVERSION})")
ax.set_xlabel("Temperatura (°C)")
ax.set_ylabel("Frecuencia")
ax.legend()
ax.grid(True)
fig.tight_layout()
ruta = CARPETA_RESULTADOS / "exploratorio_histograma.png"
fig.savefig(ruta, dpi=120)
print(f"Gráfica guardada: {ruta.relative_to(RAIZ_REPO)}")

if MOSTRAR_GRAFICAS and plt.get_backend().lower() != "agg":
    plt.show()

print("\nAnálisis exploratorio finalizado.")
