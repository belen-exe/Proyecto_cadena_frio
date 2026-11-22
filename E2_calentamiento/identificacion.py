"""
R9 - Modelo dinámico e identificación de parámetros del contenedor.

Modelo (ley de enfriamiento de Newton, primer orden):

    dT/dt = k · (T_amb(t) − T(t)),      T(t_ext) = T0

    k   [1/min] : rapidez de calentamiento (parámetro que gobierna el calentamiento)
    τ = 1/k [min]: constante de tiempo
    T_amb(t)     : temperatura ambiente MEDIDA (interpolada entre lecturas)

Discretización exacta con paso Δt (T_amb constante en el paso):

    T[n+1] = T_amb[n] + (T[n] − T_amb[n]) · exp(−k·Δt)

Método 1: PSO propio (pso.py) que minimiza la suma de cuadrados entre la
          trayectoria simulada y la medida, con parámetros θ = (k, T0).
          Intervalo al 95 % de k: linealización (jacobiano numérico),
          cov = s²·(JᵀJ)⁻¹, corregida por autocorrelación de los residuos.
Método 2: regresión lineal de la ecuación discreta (metodo2_regresion.py).

Datos: solo el tramo posterior a la extracción, temperatura interior = promedio
de los 3 canales CALIBRADOS con los coeficientes de E1.

Lee:   E2_calentamiento/datos/*.csv, descripcion no; coeficientes de E1
Crea:  E2_calentamiento/resultados/parametros_identificados.json, resumen_R9.md,
       datos_E2.png, datos_vs_modelo.png, residuos.png, convergencia_pso.png

Uso:   python E2_calentamiento/identificacion.py
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ_REPO))
sys.path.insert(0, str(CARPETA))

from comun import calibracion as cal  # noqa: E402
from comun.estadistica import t_cuantil  # noqa: E402
from metodo2_regresion import autocorrelacion_lag1, estimar_k_regresion  # noqa: E402
from pso import pso  # noqa: E402

CARPETA_DATOS = CARPETA / "datos"
CARPETA_RESULTADOS = CARPETA / "resultados"

PASO_PSO_S = 10           # promedios de 10 s para el PSO
PASO_REGRESION_S = 60     # promedios de 1 min para el método 2
LIMITES_K = (1e-4, 5e-2)  # [1/min]  (τ entre 20 min y 7 días)
LIMITES_T0 = (0.0, 15.0)  # [°C]
SEMILLAS_PSO = [0, 1, 2, 3, 4]

# ==========================================
# 1. DATOS
# ==========================================

coeficientes = cal.cargar_coeficientes()
crudos = pd.read_csv(CARPETA_DATOS / "calentamiento_E2.csv")
ambiente = pd.read_csv(CARPETA_DATOS / "ambiente_E2.csv")
eventos = pd.read_csv(CARPETA_DATOS / "eventos_E2.csv")
t_extraccion = float(eventos.loc[eventos["evento"] == "extraccion", "t_s"].iloc[0])

for c in (1, 2, 3):
    crudos[f"T_{c}"] = cal.adc_a_temperatura_calibrada(crudos[f"adc_{c}"], c, coeficientes)
crudos["T_interior"] = crudos[["T_1", "T_2", "T_3"]].mean(axis=1)


def promediar(paso_s):
    """Promedios por bloques de paso_s segundos desde la extracción."""
    tramo = crudos[crudos["t_s"] >= t_extraccion].copy()
    tramo["bloque"] = ((tramo["t_s"] - t_extraccion) // paso_s).astype(int)
    bloques = tramo.groupby("bloque").agg(t_s=("t_s", "mean"), T=("T_interior", "mean"))
    bloques["t_min"] = (bloques["t_s"] - t_extraccion) / 60
    bloques["T_amb"] = np.interp(bloques["t_s"], ambiente["t_s"], ambiente["T_amb_ref_C"])
    return bloques.reset_index(drop=True)


datos_pso = promediar(PASO_PSO_S)
datos_reg = promediar(PASO_REGRESION_S)

t_min = datos_pso["t_min"].to_numpy()
T_med = datos_pso["T"].to_numpy()
T_amb = datos_pso["T_amb"].to_numpy()
dt = float(np.median(np.diff(t_min)))

print(f"Tramo a ambiente: {t_min[-1]:.1f} min, {len(T_med)} promedios de {PASO_PSO_S} s; "
      f"T_amb media = {T_amb.mean():.2f} C")

# ==========================================
# 2. MÉTODO 1: PSO
# ==========================================


def simular(parametros, t_amb=T_amb):
    """Trayectorias del modelo para una matriz de parámetros (m × 2): columnas k, T0."""
    parametros = np.atleast_2d(parametros)
    k = parametros[:, 0]
    factor = np.exp(-k * dt)
    trayectoria = np.empty((len(parametros), len(t_min)))
    trayectoria[:, 0] = parametros[:, 1]
    for n in range(len(t_min) - 1):
        trayectoria[:, n + 1] = t_amb[n] + (trayectoria[:, n] - t_amb[n]) * factor
    return trayectoria


def identificar_pso(t_medida, t_amb, semilla):
    """Corre el PSO minimizando la SSE entre el modelo y t_medida."""
    def costo(parametros):
        return np.sum((simular(parametros, t_amb) - t_medida) ** 2, axis=1)
    return pso(costo, [LIMITES_K[0], LIMITES_T0[0]], [LIMITES_K[1], LIMITES_T0[1]], semilla=semilla)


corridas = []
for semilla in SEMILLAS_PSO:
    r = identificar_pso(T_med, T_amb, semilla)
    corridas.append(r)
    print(f"PSO semilla {semilla}: k = {r['mejor_posicion'][0]:.6f} 1/min, "
          f"T0 = {r['mejor_posicion'][1]:.4f} C, SSE = {r['mejor_costo']:.5f}")

mejor = min(corridas, key=lambda r: r["mejor_costo"])
k_pso, T0_pso = mejor["mejor_posicion"]
k_corridas = np.array([r["mejor_posicion"][0] for r in corridas])

# Intervalo de confianza por linealización (jacobiano numérico)
residuos_pso = T_med - simular(mejor["mejor_posicion"])[0]
n = len(residuos_pso)
s2 = float(residuos_pso @ residuos_pso) / (n - 2)
J = np.empty((n, 2))
for j in range(2):
    h = 1e-6 * max(abs(mejor["mejor_posicion"][j]), 1e-3)
    mas, menos = mejor["mejor_posicion"].copy(), mejor["mejor_posicion"].copy()
    mas[j] += h
    menos[j] -= h
    J[:, j] = (simular(mas)[0] - simular(menos)[0]) / (2 * h)
cov_pso = s2 * np.linalg.inv(J.T @ J)

rho_pso = autocorrelacion_lag1(residuos_pso)
rho_usado = max(rho_pso, 0.0)
cov_pso_corr = cov_pso * (1 + rho_usado) / (1 - rho_usado)
n_efectivo = n * (1 - rho_usado) / (1 + rho_usado)
t95 = t_cuantil(0.975, max(n_efectivo - 2, 1))
se_k_pso = float(np.sqrt(cov_pso_corr[0, 0]))
ic_pso_estadistico = (k_pso - t95 * se_k_pso, k_pso + t95 * se_k_pso)

# ==========================================
# 3. MÉTODO 2: REGRESIÓN
# ==========================================

reg = estimar_k_regresion(datos_reg["t_min"], datos_reg["T"], datos_reg["T_amb"])
k_reg = reg["k_1_por_min"]
ic_reg = reg["IC95"]

# ==========================================
# 3b. INCERTIDUMBRE SISTEMÁTICA (instrumentos)
# ==========================================
# El IC anterior solo refleja el ruido. Un error fijo en T_amb (termómetro de
# referencia) o en T (calibración de E1) cambia la diferencia T_amb − T que impulsa
# el calentamiento y sesga k. Se propaga re-identificando con cada entrada
# desplazada en su incertidumbre estándar (valores medidos en E1):
#   u_ref : incertidumbre estándar del termómetro de referencia
#   u_cal : RMSE de prueba de la calibración (promedio de canales, 0–45 °C)
# Luego u_k = sqrt(u_estadistica² + u_ref_k² + u_cal_k²) e IC95 = k ± 2·u_k (GUM, k = 2).

CARPETA_E1 = RAIZ_REPO / "E1_calibracion"
U_REF = json.loads((CARPETA_E1 / "datos" / "instrumento_referencia.json")
                   .read_text(encoding="utf-8"))["u_estandar_combinada_C"]
U_CAL = float(pd.read_csv(CARPETA_E1 / "resultados" / "tabla_rmse.csv")["RMSE_0_45C"].mean())

k_pso_amb = identificar_pso(T_med, T_amb + U_REF, SEMILLAS_PSO[0])["mejor_posicion"][0]
k_pso_cal = identificar_pso(T_med + U_CAL, T_amb, SEMILLAS_PSO[0])["mejor_posicion"][0]
u_sis_pso = float(np.hypot(k_pso_amb - k_pso, k_pso_cal - k_pso))
u_total_pso = float(np.hypot(se_k_pso, u_sis_pso))
ic_pso = (k_pso - 2 * u_total_pso, k_pso + 2 * u_total_pso)

k_reg_amb = estimar_k_regresion(datos_reg["t_min"], datos_reg["T"], datos_reg["T_amb"] + U_REF)["k_1_por_min"]
k_reg_cal = estimar_k_regresion(datos_reg["t_min"], datos_reg["T"] + U_CAL, datos_reg["T_amb"])["k_1_por_min"]
u_sis_reg = float(np.hypot(k_reg_amb - k_reg, k_reg_cal - k_reg))
u_total_reg = float(np.hypot(reg["se_k"], u_sis_reg))
ic_reg_estadistico = ic_reg
ic_reg = (k_reg - 2 * u_total_reg, k_reg + 2 * u_total_reg)

# ==========================================
# 4. COMPARACIÓN
# ==========================================

dif_relativa = 100 * (k_reg - k_pso) / k_pso
se_dif = np.sqrt(se_k_pso ** 2 + reg["se_k"] ** 2)  # solo parte estadística: la sistemática es común
z_dif = abs(k_reg - k_pso) / se_dif
solapan = ic_pso[0] <= ic_reg[1] and ic_reg[0] <= ic_pso[1]

print("\n========== R9: RESULTADOS ==========")
print(f"PSO       : k = {k_pso:.6f} 1/min  IC95 = [{ic_pso[0]:.6f}, {ic_pso[1]:.6f}]  "
      f"tau = {1 / k_pso:.1f} min  T0 = {T0_pso:.3f} C")
print(f"Regresión : k = {k_reg:.6f} 1/min  IC95 = [{ic_reg[0]:.6f}, {ic_reg[1]:.6f}]  "
      f"tau = {1 / k_reg:.1f} min")
print(f"Diferencia relativa: {dif_relativa:+.2f} %  ({z_dif:.2f} errores estándar); "
      f"intervalos {'se solapan' if solapan else 'NO se solapan'}")
print(f"Incertidumbre de k (PSO): estadística {se_k_pso:.2e}, sistemática {u_sis_pso:.2e}, "
      f"total {u_total_pso:.2e} 1/min  (u_ref = {U_REF} C, u_cal = {U_CAL:.4f} C)")
print(f"Dispersión de k entre {len(SEMILLAS_PSO)} corridas del PSO: "
      f"{100 * k_corridas.std() / k_corridas.mean():.2e} %")

# ==========================================
# 5. GUARDAR
# ==========================================

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

resultado = {
    "Origen": "SIMULADO",
    "modelo": "dT/dt = k·(T_amb − T)",
    "datos": {
        "tramo": "desde la extracción hasta el fin del registro",
        "duracion_min": float(t_min[-1]),
        "T_amb_media_C": float(T_amb.mean()),
        "T_extraccion_C": float(T_med[0]),
    },
    "pso": {
        "k_1_por_min": float(k_pso), "u_estadistica": se_k_pso, "u_sistematica": u_sis_pso,
        "u_total": u_total_pso, "IC95_k": list(map(float, ic_pso)),
        "IC95_k_solo_estadistico": list(map(float, ic_pso_estadistico)),
        "tau_min": float(1 / k_pso), "T0_C": float(T0_pso),
        "se_T0": float(np.sqrt(cov_pso_corr[1, 1])),
        "s_residual_C": float(np.sqrt(s2)), "rho_lag1": rho_pso, "n": n,
        "n_efectivo": float(n_efectivo),
        "k_por_semilla": k_corridas.tolist(),
        "configuracion": {"particulas": 30, "iteraciones": 150, "w": "0.9→0.4", "c1": 2.0, "c2": 2.0,
                          "limites_k": LIMITES_K, "limites_T0": LIMITES_T0},
    },
    "regresion": {
        "k_1_por_min": float(k_reg), "u_estadistica": float(reg["se_k"]), "u_sistematica": u_sis_reg,
        "u_total": u_total_reg, "IC95_k": list(map(float, ic_reg)),
        "IC95_k_solo_estadistico": list(map(float, ic_reg_estadistico)),
        "tau_min": float(1 / k_reg), "b": reg["b"], "dt_min": reg["dt_min"],
        "s_residual_C": float(reg["s_residual_C"]), "rho_lag1": reg["rho_lag1"],
        "n": reg["n"], "n_efectivo": float(reg["n_efectivo"]),
    },
    "incertidumbre_instrumentos": {"u_ref_C": U_REF, "u_cal_C": U_CAL},
    "comparacion": {"diferencia_relativa_%": float(dif_relativa), "z": float(z_dif),
                    "intervalos_se_solapan": bool(solapan)},
}
(CARPETA_RESULTADOS / "parametros_identificados.json").write_text(
    json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")

# ---- Gráfica 0: experimento completo (R8) ----
fig, ax = plt.subplots(figsize=(12, 5))
for c in (1, 2, 3):
    ax.plot(crudos["t_s"] / 60, crudos[f"T_{c}"], lw=0.4, alpha=0.7, label=f"Canal {c} (calibrado)")
ax.plot(ambiente["t_s"] / 60, ambiente["T_amb_ref_C"], "k.", ms=3, label="Ambiente (referencia)")
ax.axvline(t_extraccion / 60, color="tab:red", ls="--", label="Extracción de la nevera")
ax.axhline(8, color="gray", ls=":", label="Límite 8 °C")
ax.set_xlabel("Tiempo (min)")
ax.set_ylabel("Temperatura (°C)")
ax.set_title("E2 - Registro completo: nevera y exposición a ambiente - SIMULADO")
ax.grid(True, alpha=0.4)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "datos_E2.png", dpi=120)

# ---- Gráfica 1: datos vs modelo ----
trayectoria_reg = simular([[k_reg, T_med[0]]])[0]
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t_min, T_med, ".", ms=3, color="gray", label=f"Medido (promedio 3 canales, bloques de {PASO_PSO_S} s)")
ax.plot(t_min, simular(mejor["mejor_posicion"])[0], lw=2, label=f"Modelo PSO (k = {k_pso:.5f} 1/min)")
ax.plot(t_min, trayectoria_reg, "--", lw=2, label=f"Modelo regresión (k = {k_reg:.5f} 1/min)")
ax.set_xlabel("Tiempo desde la extracción (min)")
ax.set_ylabel("Temperatura interior (°C)")
ax.set_title("E2 - Datos vs modelo de primer orden - SIMULADO")
ax.grid(True, alpha=0.4)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "datos_vs_modelo.png", dpi=120)

# ---- Gráfica 2: residuos ----
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5))
ax1.plot(t_min, residuos_pso, ".", ms=3)
ax1.axhline(0, color="k", lw=0.8)
ax1.set_title(f"Residuos PSO vs tiempo (ρ1 = {rho_pso:.2f})")
ax1.set_xlabel("Tiempo (min)")
ax1.set_ylabel("Medido − modelo (°C)")
ax2.hist(residuos_pso, bins=30)
ax2.set_title("Histograma de residuos PSO")
ax2.set_xlabel("°C")
ax3.plot(datos_reg["t_min"].to_numpy()[:-1], reg["residuos"], "o", ms=3)
ax3.axhline(0, color="k", lw=0.8)
ax3.set_title(f"Residuos regresión (error de ecuación, ρ1 = {reg['rho_lag1']:.2f})")
ax3.set_xlabel("Tiempo (min)")
for ax in (ax1, ax2, ax3):
    ax.grid(True, alpha=0.4)
fig.suptitle("E2 - Residuos - SIMULADO")
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "residuos.png", dpi=120)

# ---- Gráfica 3: convergencia del PSO ----
fig, ax = plt.subplots(figsize=(8, 4.5))
for semilla, r in zip(SEMILLAS_PSO, corridas):
    ax.semilogy(r["historia"], label=f"Semilla {semilla}")
ax.set_xlabel("Iteración")
ax.set_ylabel("Mejor SSE (°C²)")
ax.set_title("E2 - Convergencia del PSO - SIMULADO")
ax.grid(True, which="both", alpha=0.4)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "convergencia_pso.png", dpi=120)

# ---- Resumen ----
resumen = f"""# Resultados R9 — Modelo dinámico e identificación

> Generado por `E2_calentamiento/identificacion.py`. Datos **SIMULADOS**.

## Modelo

dT/dt = k·(T_amb(t) − T),  T(t_ext) = T0.  Solución exacta por paso (Δt):
T[n+1] = T_amb[n] + (T[n] − T_amb[n])·e^(−k·Δt).  τ = 1/k.

Datos: {t_min[-1]:.0f} min posteriores a la extracción; T interior = promedio de los 3 canales
calibrados (E1); T_amb medida cada 60 s e interpolada. T_amb media = {T_amb.mean():.2f} °C.

## Resultados

| Método | k [1/min] | u estadística | u sistemática | **IC 95 % de k [1/min]** | τ [min] | Otros |
|---|---|---|---|---|---|---|
| 1. PSO propio (k, T0) | {k_pso:.6f} | {se_k_pso:.2e} | {u_sis_pso:.2e} | **[{ic_pso[0]:.6f}, {ic_pso[1]:.6f}]** | {1 / k_pso:.1f} | T0 = {T0_pso:.3f} °C, s = {np.sqrt(s2):.4f} °C |
| 2. Regresión de la ecuación discreta | {k_reg:.6f} | {reg['se_k']:.2e} | {u_sis_reg:.2e} | **[{ic_reg[0]:.6f}, {ic_reg[1]:.6f}]** | {1 / k_reg:.1f} | b = {reg['b']:.6f}, Δt = {reg['dt_min']:.0f} min |

- Diferencia relativa: **{dif_relativa:+.2f} %** ({z_dif:.2f} errores estándar combinados);
  los intervalos {"se solapan: ambos métodos son comparables" if solapan else "NO se solapan"}.
- El PSO se corrió con {len(SEMILLAS_PSO)} semillas: dispersión relativa de k =
  {100 * k_corridas.std() / k_corridas.mean():.1e} % (converge siempre al mismo mínimo,
  ver `convergencia_pso.png`).

## Cálculo del intervalo al 95 % de k

- **PSO:** linealización alrededor del óptimo. J = ∂T_modelo/∂θ por diferencias centrales;
  cov(θ) = s²·(JᵀJ)⁻¹ con s² = SSE/(n − 2). Como los residuos de puntos vecinos están
  correlacionados (ρ1 = {rho_pso:.2f}), la covarianza se multiplica por (1+ρ1)/(1−ρ1) y se usa
  n_efectivo = n·(1−ρ1)/(1+ρ1) = {n_efectivo:.0f} para los grados de libertad.
  IC = k ± t(0,975; n_ef − 2)·σ_k.
- **Parte sistemática (ambos métodos):** se repite la identificación con T_amb + u_ref
  (u_ref = {U_REF} °C, termómetro de referencia, E1) y con T + u_cal (u_cal = {U_CAL:.4f} °C,
  RMSE de prueba de la calibración, E1); u_sis = √(Δk_ref² + Δk_cal²).
- **Combinación:** u_k = √(u_estadística² + u_sis²); IC 95 % = k ± 2·u_k (factor de cobertura 2).
  Con solo la parte estadística el IC del PSO sería [{ic_pso_estadistico[0]:.6f}, {ic_pso_estadistico[1]:.6f}],
  demasiado optimista: el error de los instrumentos domina.
- **Regresión:** σ_b de mínimos cuadrados (con la misma corrección por autocorrelación,
  ρ1 = {reg['rho_lag1']:.2f}) y propagación a k = −ln(1−b)/Δt: σ_k = σ_b/((1−b)·Δt).

## Por qué pueden diferir

El PSO ajusta la trayectoria completa (error de salida) y estima también T0; la
regresión solo relaciona cada minuto con el siguiente (error de ecuación) y es más
sensible al ruido de los incrementos, por eso su intervalo es más ancho.

Gráficas: `datos_E2.png`, `datos_vs_modelo.png`, `residuos.png`, `convergencia_pso.png`.
"""
(CARPETA_RESULTADOS / "resumen_R9.md").write_text(resumen, encoding="utf-8")
print(f"\nGenerado en {CARPETA_RESULTADOS.relative_to(RAIZ_REPO)}: parametros_identificados.json, "
      "resumen_R9.md, datos_E2.png, datos_vs_modelo.png, residuos.png, convergencia_pso.png")
