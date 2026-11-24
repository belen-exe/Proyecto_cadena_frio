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
Método 2: regresión lineal de la ecuación discreta (metodo2_regresion.py).
          De aquí sale el INTERVALO AL 95 % de k.

Los dos métodos son comparables si el k del PSO cae dentro del intervalo del método 2.

Datos: solo el tramo posterior a la extracción; temperatura interior = promedio
de los 3 canales CALIBRADOS con los coeficientes de E1.

Lee:   E2_calentamiento/datos/*.csv y los coeficientes de E1
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


def simular(parametros):
    """Trayectorias del modelo para una matriz de parámetros (m × 2): columnas k, T0."""
    parametros = np.atleast_2d(parametros)
    factor = np.exp(-parametros[:, 0] * dt)
    trayectoria = np.empty((len(parametros), len(t_min)))
    trayectoria[:, 0] = parametros[:, 1]
    for n in range(len(t_min) - 1):
        trayectoria[:, n + 1] = T_amb[n] + (trayectoria[:, n] - T_amb[n]) * factor
    return trayectoria


def costo(parametros):
    """Suma de errores al cuadrado entre el modelo y la medición."""
    return np.sum((simular(parametros) - T_med) ** 2, axis=1)


corridas = []
for semilla in SEMILLAS_PSO:
    r = pso(costo, [LIMITES_K[0], LIMITES_T0[0]], [LIMITES_K[1], LIMITES_T0[1]], semilla=semilla)
    corridas.append(r)
    print(f"PSO semilla {semilla}: k = {r['mejor_posicion'][0]:.6f} 1/min, "
          f"T0 = {r['mejor_posicion'][1]:.4f} C, SSE = {r['mejor_costo']:.5f}")

mejor = min(corridas, key=lambda r: r["mejor_costo"])
k_pso, T0_pso = mejor["mejor_posicion"]
k_corridas = np.array([r["mejor_posicion"][0] for r in corridas])

residuos_pso = T_med - simular(mejor["mejor_posicion"])[0]
s_pso = float(np.sqrt(residuos_pso @ residuos_pso / (len(residuos_pso) - 2)))
rho_pso = autocorrelacion_lag1(residuos_pso)

# ==========================================
# 3. MÉTODO 2: REGRESIÓN (y el intervalo al 95 % de k)
# ==========================================

reg = estimar_k_regresion(datos_reg["t_min"], datos_reg["T"], datos_reg["T_amb"])
k_reg = reg["k_1_por_min"]
ic_k = reg["IC95"]

# ==========================================
# 4. COMPARACIÓN
# ==========================================

dif_relativa = 100 * (k_reg - k_pso) / k_pso
pso_dentro_ic = ic_k[0] <= k_pso <= ic_k[1]

print("\n========== R9: RESULTADOS ==========")
print(f"PSO       : k = {k_pso:.6f} 1/min  tau = {1 / k_pso:.1f} min  T0 = {T0_pso:.3f} C")
print(f"Regresión : k = {k_reg:.6f} 1/min  tau = {1 / k_reg:.1f} min")
print(f"Intervalo al 95 % de k (regresión): [{ic_k[0]:.6f}, {ic_k[1]:.6f}] 1/min")
print(f"Diferencia relativa: {dif_relativa:+.2f} %; el k del PSO "
      f"{'está' if pso_dentro_ic else 'NO está'} dentro del intervalo")
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
        "k_1_por_min": float(k_pso), "tau_min": float(1 / k_pso), "T0_C": float(T0_pso),
        "s_residual_C": s_pso, "rho_lag1": rho_pso,
        "k_por_semilla": k_corridas.tolist(),
        "configuracion": {"particulas": 30, "iteraciones": 150, "w": "0.9→0.4", "c1": 2.0, "c2": 2.0,
                          "limites_k": LIMITES_K, "limites_T0": LIMITES_T0},
    },
    "regresion": {
        "k_1_por_min": float(k_reg), "se_k": float(reg["se_k"]), "IC95_k": list(map(float, ic_k)),
        "tau_min": float(1 / k_reg), "b": reg["b"], "se_b": reg["se_b"], "dt_min": reg["dt_min"],
        "s_residual_C": float(reg["s_residual_C"]), "rho_lag1": reg["rho_lag1"],
        "n": reg["n"], "n_efectivo": float(reg["n_efectivo"]),
    },
    "intervalo_k": {"metodo": "regresion (método 2)", "IC95": list(map(float, ic_k))},
    "comparacion": {"diferencia_relativa_%": float(dif_relativa),
                    "k_pso_dentro_del_intervalo": bool(pso_dentro_ic)},
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
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t_min, T_med, ".", ms=3, color="gray", label=f"Medido (promedio 3 canales, bloques de {PASO_PSO_S} s)")
ax.plot(t_min, simular(mejor["mejor_posicion"])[0], lw=2, label=f"Modelo PSO (k = {k_pso:.5f} 1/min)")
ax.plot(t_min, simular([[k_reg, T_med[0]]])[0], "--", lw=2, label=f"Modelo regresión (k = {k_reg:.5f} 1/min)")
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
ax3.set_title(f"Residuos regresión (ρ1 = {reg['rho_lag1']:.2f})")
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

| Método | k [1/min] | τ [min] | Otros |
|---|---|---|---|
| 1. PSO propio (k, T0) | {k_pso:.6f} | {1 / k_pso:.1f} | T0 = {T0_pso:.3f} °C, s = {s_pso:.4f} °C |
| 2. Regresión de la ecuación discreta | {k_reg:.6f} | {1 / k_reg:.1f} | b = {reg['b']:.6f}, Δt = {reg['dt_min']:.0f} min |

**Intervalo al 95 % de la rapidez de calentamiento k: [{ic_k[0]:.6f}, {ic_k[1]:.6f}] min⁻¹**
(τ entre {1 / ic_k[1]:.0f} y {1 / ic_k[0]:.0f} min).

- Diferencia relativa entre métodos: **{dif_relativa:+.2f} %**. El k del PSO
  {"está dentro del intervalo: ambos métodos son comparables" if pso_dentro_ic else "NO está dentro del intervalo"}.
- El PSO se corrió con {len(SEMILLAS_PSO)} semillas: dispersión relativa de k =
  {100 * k_corridas.std() / k_corridas.mean():.1e} % (converge siempre al mismo mínimo,
  ver `convergencia_pso.png`).

## Cálculo del intervalo al 95 % de k

1. La regresión ΔT = b·(T_amb − T) se resuelve con θ = (XᵀX)⁻¹·Xᵀ·y (igual que en E1);
   el error estándar de b sale de cov = s²·(XᵀX)⁻¹: σ_b = {reg['se_b']:.2e}.
2. **Autocorrelación:** si cada residuo se parece al anterior (ρ1 = {reg['rho_lag1']:.2f}), los
   datos traen menos información independiente. Se usa n_efectivo = n·(1−ρ1)/(1+ρ1)
   = {reg['n_efectivo']:.0f} (de n = {reg['n']}) y σ_b se multiplica por √((1+ρ1)/(1−ρ1)).
   Si ρ1 ≤ 0 no se corrige.
3. Paso de b a k = −ln(1−b)/Δt con la derivada: σ_k = σ_b/((1−b)·Δt) = {reg['se_k']:.2e} min⁻¹.
4. IC 95 % = k ± t·σ_k, con t de la tabla t para n_efectivo − 1 grados de libertad.

Limitación: el intervalo solo considera el ruido de las mediciones; no incluye el
error fijo de los instrumentos (termómetro de referencia y calibración de E1).

## Por qué pueden diferir los métodos

El PSO ajusta la trayectoria completa y estima también T0; la regresión solo relaciona
cada minuto con el siguiente y es más sensible al ruido de los incrementos.

Gráficas: `datos_E2.png`, `datos_vs_modelo.png`, `residuos.png`, `convergencia_pso.png`.
"""
(CARPETA_RESULTADOS / "resumen_R9.md").write_text(resumen, encoding="utf-8")
print(f"\nGenerado en {CARPETA_RESULTADOS.relative_to(RAIZ_REPO)}: parametros_identificados.json, "
      "resumen_R9.md, datos_E2.png, datos_vs_modelo.png, residuos.png, convergencia_pso.png")
