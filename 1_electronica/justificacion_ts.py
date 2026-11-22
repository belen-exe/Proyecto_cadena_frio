"""
R2 - Justificación numérica del periodo de muestreo Ts.

Ts se acota con:
  (a) las dinámicas observadas en los datos de E3 (SIMULADOS): ruido en operación
      normal, rapidez de calentamiento durante las aperturas y forma del escalón
      de una desconexión;
  (b) los requisitos de detección de R13: retardo ≤ 20 s en desconexiones y
      ≤ 60 s en aperturas;
  (c) el límite inferior que imponen la transmisión serie y la lectura del ADC.

Las temperaturas usan la conversión β NOMINAL (provisional, sin calibrar);
cuando exista la calibración de E1 conviene volver a ejecutar este script.

Lee:   E3_eventos/datos/entrenamiento.csv, prueba.csv, tabla_eventos.csv
Crea:  1_electronica/resultados/justificacion_Ts.md

Uso:   python 1_electronica/justificacion_ts.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

CARPETA_E3 = RAIZ_REPO / "E3_eventos" / "datos"
CARPETA_RESULTADOS = Path(__file__).resolve().parent / "resultados"

# ==========================================
# PARÁMETROS DE DISEÑO
# ==========================================

TS_ELEGIDO_S = 1.0           # Debe coincidir con TS_MS del firmware

RETARDO_MAX_DESCONEXION_S = 20.0   # R13
RETARDO_MAX_APERTURA_S = 60.0      # R13
DURACION_APERTURA_S = 30.0         # R11

# El detector confirmará una anomalía solo tras K muestras consecutivas anómalas
# (rechaza picos aislados de ruido). Peor caso de retardo ante un escalón: K·Ts.
K_CONFIRMACION = 3

# Mínimo de muestras dentro de una apertura de 30 s para poder filtrar el ruido
# (promedio móvil) y aun así ver el evento mientras ocurre.
MUESTRAS_MIN_POR_APERTURA = 10

BAUDIOS = 115200
BITS_POR_BYTE_SERIE = 10     # 8 datos + 1 inicio + 1 parada
LINEA_EJEMPLO = "3600123,2953,2941,2960,5.05,5.36,4.82,0,SIMULADO\r\n"
TIEMPO_ADC_POR_CANAL_S = 100e-6   # analogRead del ESP32: decenas de µs (cota holgada)
FACTOR_SEGURIDAD_INFERIOR = 2.0

# ==========================================
# (a) DINÁMICAS EN LOS DATOS DE E3
# ==========================================

entrenamiento = pd.read_csv(CARPETA_E3 / "entrenamiento.csv")
prueba = pd.read_csv(CARPETA_E3 / "prueba.csv")
eventos = pd.read_csv(CARPETA_E3 / "tabla_eventos.csv")
canales = [c for c in entrenamiento.columns if c.startswith("adc_")]

# Ruido en operación normal (entrenamiento)
ruido_cuentas = entrenamiento[canales].std()
temp_entrenamiento = pd.DataFrame({c: ms.adc_a_temperatura_beta(entrenamiento[c]) for c in canales})
ruido_c = temp_entrenamiento.std()

# Rapidez de calentamiento durante cada apertura: pendiente por mínimos cuadrados
temp_prueba = pd.DataFrame({c: ms.adc_a_temperatura_beta(prueba[c]) for c in canales})
pendientes = []
for _, ev in eventos[eventos["tipo"] == "apertura"].iterrows():
    dentro = (prueba["t_s"] >= ev["t_inicio_s"]) & (prueba["t_s"] < ev["t_fin_s"])
    t = prueba.loc[dentro, "t_s"].to_numpy()
    fila = {"t_inicio_s": ev["t_inicio_s"]}
    for c in canales:
        y = temp_prueba.loc[dentro, c].to_numpy()
        a = np.column_stack([np.ones_like(t), t])
        coef = np.linalg.lstsq(a, y, rcond=None)[0]
        fila[c] = coef[1]  # °C/s
    pendientes.append(fila)
pendientes = pd.DataFrame(pendientes)
# Canal más expuesto y su pendiente media (más robusta al ruido que el máximo)
canal_mas_rapido = pendientes[canales].mean().idxmax()
pendiente_max = pendientes[canal_mas_rapido].mean()      # °C/s

# Cambio por muestra con el Ts elegido, comparado con el ruido
cambio_por_muestra = pendiente_max * TS_ELEGIDO_S
ruido_canal_rapido = ruido_c[canal_mas_rapido]
tiempo_para_3_sigma = 3 * ruido_canal_rapido / pendiente_max

# Desconexión: muestras intermedias entre la última lectura normal y la saturación
muestras_transicion = []
for _, ev in eventos[eventos["tipo"] == "desconexion"].iterrows():
    c = f"adc_{int(ev['sensor'])}"
    ventana = prueba[(prueba["t_s"] >= ev["t_inicio_s"] - 5) & (prueba["t_s"] < ev["t_inicio_s"] + 5)][c]
    intermedias = ((ventana > ventana.iloc[0] + 50) & (ventana < ms.ADC_LIMITE_SUPERIOR)).sum()
    muestras_transicion.append(int(intermedias))

# ==========================================
# (b) COTAS SUPERIORES DESDE R13
# ==========================================

ts_max_desconexion = RETARDO_MAX_DESCONEXION_S / K_CONFIRMACION
ts_max_apertura = DURACION_APERTURA_S / MUESTRAS_MIN_POR_APERTURA
ts_max = min(ts_max_desconexion, ts_max_apertura)

# ==========================================
# (c) COTA INFERIOR: transmisión serie y ADC
# ==========================================

bytes_linea = len(LINEA_EJEMPLO)
tiempo_serie_s = bytes_linea * BITS_POR_BYTE_SERIE / BAUDIOS
tiempo_adc_s = ms.NUM_SENSORES * TIEMPO_ADC_POR_CANAL_S
ts_min = FACTOR_SEGURIDAD_INFERIOR * (tiempo_serie_s + tiempo_adc_s)

# ==========================================
# CONSECUENCIAS DEL Ts ELEGIDO
# ==========================================

retardo_desconexion_peor = K_CONFIRMACION * TS_ELEGIDO_S
muestras_por_apertura = DURACION_APERTURA_S / TS_ELEGIDO_S
muestras_por_hora = 3600 / TS_ELEGIDO_S
kb_por_hora = muestras_por_hora * bytes_linea / 1024
ocupacion_serie = (tiempo_serie_s + tiempo_adc_s) / TS_ELEGIDO_S * 100

cumple = ts_min <= TS_ELEGIDO_S <= ts_max

# ==========================================
# SALIDAS
# ==========================================

filas_ruido = "\n".join(
    f"| {c} | {ruido_cuentas[c]:.2f} | {ruido_c[c]:.3f} |" for c in canales
)
filas_pend = "\n".join(
    f"| {int(r['t_inicio_s'])} | " + " | ".join(f"{r[c] * 60:.3f}" for c in canales) + " |"
    for _, r in pendientes.iterrows()
)

informe = f"""# Justificación numérica de Ts (R2)

> Generado por `1_electronica/justificacion_ts.py` con los datos **SIMULADOS** de E3.
> Temperaturas con la conversión β nominal (**provisional, sin calibrar**).

## (a) Dinámicas observadas en los datos

**Ruido en operación normal** (entrenamiento, 30 min):

| Canal | σ [cuentas] | σ [°C] |
|---|---|---|
{filas_ruido}

**Rapidez de calentamiento durante las aperturas** (pendiente por mínimos cuadrados
dentro de cada apertura de 30 s, en °C/min):

| Inicio [s] | {" | ".join(canales)} |
|---|{"---|" * len(canales)}
{filas_pend}

- Pendiente media del canal más expuesto: **{pendiente_max * 60:.3f} °C/min** ({pendiente_max:.4f} °C/s, canal {canal_mas_rapido}).
- Con Ts = {TS_ELEGIDO_S:g} s la temperatura cambia {cambio_por_muestra:.4f} °C por muestra,
  {cambio_por_muestra / ruido_canal_rapido:.2f} veces el ruido: una muestra sola no basta y el detector
  debe acumular varias. El cambio alcanza 3σ de ruido tras **{tiempo_para_3_sigma:.0f} s**, dentro de
  los {RETARDO_MAX_APERTURA_S:.0f} s permitidos. Muestrear más rápido no acelera esto: lo fija la física.
- **Desconexión:** el ADC salta a la saturación en un solo paso (muestras intermedias por
  evento: {muestras_transicion}). Es un escalón: su retardo de detección depende solo de Ts.

## (b) Cotas superiores desde R13

El detector confirma una anomalía con K = {K_CONFIRMACION} muestras consecutivas
(para rechazar picos aislados).

| Condición | Cálculo | Ts máximo |
|---|---|---|
| Desconexión detectada en ≤ {RETARDO_MAX_DESCONEXION_S:.0f} s | K·Ts ≤ {RETARDO_MAX_DESCONEXION_S:.0f} s → Ts ≤ {RETARDO_MAX_DESCONEXION_S:.0f}/{K_CONFIRMACION} | {ts_max_desconexion:.2f} s |
| ≥ {MUESTRAS_MIN_POR_APERTURA} muestras dentro de una apertura de {DURACION_APERTURA_S:.0f} s | Ts ≤ {DURACION_APERTURA_S:.0f}/{MUESTRAS_MIN_POR_APERTURA} | {ts_max_apertura:.2f} s |
| **Cota superior** | mínimo de las dos | **{ts_max:.2f} s** |

## (c) Cota inferior

| Tarea por ciclo | Tiempo |
|---|---|
| Enviar una línea de {bytes_linea} bytes a {BAUDIOS} baudios | {tiempo_serie_s * 1e3:.2f} ms |
| Leer {ms.NUM_SENSORES} canales del ADC (cota holgada) | {tiempo_adc_s * 1e3:.2f} ms |
| **Cota inferior** (factor de seguridad {FACTOR_SEGURIDAD_INFERIOR:g}) | **{ts_min * 1e3:.1f} ms** |

## Decisión

Intervalo admisible: {ts_min * 1e3:.1f} ms ≤ Ts ≤ {ts_max:.2f} s. **Ts = {TS_ELEGIDO_S:g} s**
({"cumple" if cumple else "NO cumple"}), porque:

- retardo de peor caso ante una desconexión = {retardo_desconexion_peor:.0f} s, con margen
  {RETARDO_MAX_DESCONEXION_S / retardo_desconexion_peor:.1f}× frente a 20 s;
- da {muestras_por_apertura:.0f} muestras por apertura, suficientes para promediar ruido;
- ocupa el {ocupacion_serie:.2f} % del ciclo en transmisión y lectura, y genera
  {muestras_por_hora:.0f} filas/h (≈ {kb_por_hora:.0f} KB/h), un volumen fácil de manejar;
- un Ts menor no mejora la detección de aperturas (la limita la rapidez física de
  calentamiento) y solo multiplica los datos.
"""

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
ruta = CARPETA_RESULTADOS / "justificacion_Ts.md"
ruta.write_text(informe, encoding="utf-8")

print(f"Pendiente media del canal mas expuesto: {pendiente_max * 60:.3f} C/min ({canal_mas_rapido})")
print(f"Ruido (entrenamiento) [C]: " + ", ".join(f"{c}={ruido_c[c]:.3f}" for c in canales))
print(f"Tiempo para subir 3 sigma: {tiempo_para_3_sigma:.0f} s")
print(f"Ts admisible: {ts_min * 1e3:.1f} ms <= Ts <= {ts_max:.2f} s; elegido {TS_ELEGIDO_S:g} s -> "
      f"{'CUMPLE' if cumple else 'NO CUMPLE'}")
print(f"Generado: {ruta.relative_to(RAIZ_REPO)}")
