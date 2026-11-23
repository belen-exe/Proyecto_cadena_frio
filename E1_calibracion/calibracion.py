"""
R5, R6, R7 - Calibración ADC -> temperatura con álgebra matricial propia.

Pasos
-----
1. Promedia las N lecturas ADC de cada escalón (reduce el ruido del ADC).
2. R5: ajusta 3 estructuras de complejidad creciente (comun/calibracion.py) SOLO con
   los puntos de calibración y elige una con un criterio de generalización:
   el RMSE de validación cruzada dejando uno fuera (LOO), promediado en los canales.
   Regla de parsimonia: la estructura más simple cuyo RMSE_LOO no supere en más de
   un 5 % al mínimo.
3. R6: con la estructura elegida, por canal: coeficientes ± error estándar,
   intervalo de predicción al 95 %, condiciones de optimalidad (gradiente nulo y
   hessiano definido positivo) y confiabilidad numérica (número de condición y
   comparación QR / ecuaciones normales / SVD). Contraste declarado con
   numpy.linalg.lstsq (función de librería, SOLO como contraste).
4. R7: RMSE sobre los puntos de PRUEBA (que no se usaron en nada de lo anterior),
   en 0–45 °C y en 0–10 °C, con análisis del error.

Lee:   E1_calibracion/datos/calibracion_E1.csv, instrumento_referencia.json
Crea:  E1_calibracion/resultados/ (coeficientes_calibracion.json, tablas CSV,
       resumen_E1.md y gráficas PNG)

Uso:   python E1_calibracion/calibracion.py
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import calibracion as cal  # noqa: E402
from comun import modelo_sensor as ms  # noqa: E402
from comun.estadistica import ajustar_mco, intervalo_prediccion, rmse, t_cuantil  # noqa: E402

CARPETA = Path(__file__).resolve().parent
CARPETA_DATOS = CARPETA / "datos"
CARPETA_RESULTADOS = CARPETA / "resultados"

CANALES = [1, 2, 3]
META_RMSE_TOTAL = 0.6
META_RMSE_0_10 = 0.4
TOLERANCIA_PARSIMONIA = 1.05

# ==========================================
# 1. CARGAR Y PROMEDIAR POR ESCALÓN
# ==========================================

crudos = pd.read_csv(CARPETA_DATOS / "calibracion_E1.csv")
referencia = json.loads((CARPETA_DATOS / "instrumento_referencia.json").read_text(encoding="utf-8"))
U_REF = referencia["u_estandar_combinada_C"]

puntos = crudos.groupby("punto").agg(
    tipo=("tipo", "first"),
    T_ref_C=("T_ref_C", "first"),
    **{f"adc_{c}": (f"adc_{c}", "mean") for c in CANALES},
    **{f"sd_adc_{c}": (f"adc_{c}", "std") for c in CANALES},
).reset_index()

calib = puntos[puntos["tipo"] == "calibracion"].reset_index(drop=True)
prueba = puntos[puntos["tipo"] == "prueba"].reset_index(drop=True)

print(f"Puntos de calibración: {len(calib)}  |  puntos de prueba: {len(prueba)}")
print(f"Incertidumbre estándar de la referencia: {U_REF} C ({referencia['instrumento']})")

# ==========================================
# 2. R5 - COMPARACIÓN DE ESTRUCTURAS (solo datos de calibración)
# ==========================================


def rmse_loo(adc, temperatura, estructura):
    """RMSE [°C] de validación cruzada dejando uno fuera."""
    errores = []
    for i in range(len(adc)):
        mascara = np.arange(len(adc)) != i
        ajuste = ajustar_mco(cal.matriz_diseno(adc[mascara], estructura),
                             cal.objetivo(temperatura[mascara], estructura))
        t_hat = cal.predecir(adc[i:i + 1], estructura, ajuste["theta"])[0]
        errores.append(temperatura[i] - t_hat)
    return rmse(errores)


filas_modelos = []
for estructura, info in cal.ESTRUCTURAS.items():
    for c in CANALES:
        adc = calib[f"adc_{c}"].to_numpy()
        temp = calib["T_ref_C"].to_numpy()
        ajuste = ajustar_mco(cal.matriz_diseno(adc, estructura), cal.objetivo(temp, estructura))
        t_hat = cal.predecir(adc, estructura, ajuste["theta"])
        t_hat_prueba = cal.predecir(prueba[f"adc_{c}"].to_numpy(), estructura, ajuste["theta"])
        filas_modelos.append({
            "estructura": estructura,
            "num_parametros": info["num_parametros"],
            "canal": c,
            "RMSE_entrenamiento_C": rmse(temp - t_hat),
            "RMSE_LOO_C": rmse_loo(adc, temp, estructura),
            "RMSE_prueba_C (informativo)": rmse(prueba["T_ref_C"] - t_hat_prueba),
            "cond_X": ajuste["diagnostico"]["numero_condicion_X"],
        })

tabla_modelos = pd.DataFrame(filas_modelos)
resumen_modelos = tabla_modelos.groupby("estructura", sort=False).agg(
    num_parametros=("num_parametros", "first"),
    RMSE_entrenamiento_C=("RMSE_entrenamiento_C", "mean"),
    RMSE_LOO_C=("RMSE_LOO_C", "mean"),
).reset_index()

loo_min = resumen_modelos["RMSE_LOO_C"].min()
candidatas = resumen_modelos[resumen_modelos["RMSE_LOO_C"] <= TOLERANCIA_PARSIMONIA * loo_min]
ESTRUCTURA = candidatas.sort_values("num_parametros", kind="stable").iloc[0]["estructura"]

print("\n========== R5: COMPARACIÓN DE ESTRUCTURAS (promedio de canales) ==========")
print(resumen_modelos.round(4).to_string(index=False))
print(f"Estructura seleccionada: {ESTRUCTURA}  ({cal.ESTRUCTURAS[ESTRUCTURA]['ecuacion']})")

# ==========================================
# 3. R6 - AJUSTE FINAL POR CANAL
# ==========================================

coeficientes = {
    "estructura": ESTRUCTURA,
    "ecuacion": cal.ESTRUCTURAS[ESTRUCTURA]["ecuacion"],
    "espacio_ajuste": cal.ESTRUCTURAS[ESTRUCTURA]["espacio"],
    "Origen": "SIMULADO",
    "canales": {},
}
filas_coef, filas_diag, filas_rmse = [], [], []
ajustes = {}

for c in CANALES:
    adc = calib[f"adc_{c}"].to_numpy()
    temp = calib["T_ref_C"].to_numpy()
    X = cal.matriz_diseno(adc, ESTRUCTURA)
    y = cal.objetivo(temp, ESTRUCTURA)
    ajuste = ajustar_mco(X, y)
    ajustes[c] = ajuste

    # Contraste con una función de librería (numpy.linalg.lstsq): SOLO CONTRASTE
    theta_lstsq = np.linalg.lstsq(X, y, rcond=None)[0]
    dif_lstsq = float(np.max(np.abs(ajuste["theta"] - theta_lstsq) / np.abs(theta_lstsq)))

    coeficientes["canales"][str(c)] = {
        "theta": ajuste["theta"].tolist(),
        "error_estandar": ajuste["error_estandar"].tolist(),
        "cov": ajuste["cov"].tolist(),
        "XtX_inv": ajuste["XtX_inv"].tolist(),
        "s": ajuste["s"],
        "gl": ajuste["gl"],
    }

    t95 = t_cuantil(0.975, ajuste["gl"])
    for j, (theta, ee) in enumerate(zip(ajuste["theta"], ajuste["error_estandar"])):
        filas_coef.append({
            "canal": c, "parametro": f"θ{j}", "valor": theta, "error_estandar": ee,
            "IC95_inf": theta - t95 * ee, "IC95_sup": theta + t95 * ee,
            "error_relativo_%": 100 * ee / abs(theta),
        })

    d = ajuste["diagnostico"]
    filas_diag.append({
        "canal": c,
        "max|∇J|": d["norma_gradiente"],
        "|Xᵀr| relativo": d["norma_gradiente_relativa"],
        "λmin(∇²J)": d["autovalor_min_hessiano"],
        "λmax(∇²J)": d["autovalor_max_hessiano"],
        "cond(X)": d["numero_condicion_X"],
        "cond(XᵀX)": d["numero_condicion_XtX"],
        "dif QR-normales": d["dif_rel_max_QR_vs_normales"],
        "dif QR-SVD": d["dif_rel_max_QR_vs_SVD"],
        "dif QR-lstsq (contraste)": dif_lstsq,
    })

    # ---- R7: evaluación en los puntos de prueba ----
    adc_p = prueba[f"adc_{c}"].to_numpy()
    t_ref_p = prueba["T_ref_C"].to_numpy()
    t_hat_p = cal.predecir(adc_p, ESTRUCTURA, ajuste["theta"])
    error = t_ref_p - t_hat_p

    y_hat, semiancho = intervalo_prediccion(cal.matriz_diseno(adc_p, ESTRUCTURA), ajuste)
    lim_a = cal.respuesta_a_temperatura(y_hat - semiancho, ESTRUCTURA)
    lim_b = cal.respuesta_a_temperatura(y_hat + semiancho, ESTRUCTURA)
    dentro_ip = (t_ref_p >= np.minimum(lim_a, lim_b)) & (t_ref_p <= np.maximum(lim_a, lim_b))

    zona = t_ref_p <= 10
    filas_rmse.append({
        "canal": c,
        "RMSE_0_45C": rmse(error),
        "RMSE_0_10C": rmse(error[zona]),
        "n_prueba": len(error),
        "n_prueba_0_10C": int(zona.sum()),
        "sesgo_medio_C": float(np.mean(error)),
        "desv_est_C": float(np.std(error)),
        "error_max_abs_C": float(np.max(np.abs(error))),
        "semiancho_IP95_medio_C": float(np.mean(np.abs(lim_b - lim_a) / 2)),
        "cobertura_IP95_%": 100 * float(dentro_ip.mean()),
        "cumple_0_45": rmse(error) <= META_RMSE_TOTAL,
        "cumple_0_10": rmse(error[zona]) <= META_RMSE_0_10,
    })

tabla_coef = pd.DataFrame(filas_coef)
tabla_diag = pd.DataFrame(filas_diag)
tabla_rmse = pd.DataFrame(filas_rmse)

print("\n========== R6: COEFICIENTES ==========")
print(tabla_coef[["canal", "parametro", "valor", "error_estandar", "error_relativo_%"]]
      .to_string(index=False, float_format=lambda v: f"{v:.6g}"))
print("\n========== R6: OPTIMALIDAD Y CONFIABILIDAD NUMÉRICA ==========")
print(tabla_diag.to_string(index=False, float_format=lambda v: f"{v:.3e}"))
print("\n========== R7: RMSE EN PUNTOS DE PRUEBA ==========")
print(tabla_rmse.round(4).to_string(index=False))

# ==========================================
# 4. GUARDAR RESULTADOS
# ==========================================

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
(CARPETA_RESULTADOS / "coeficientes_calibracion.json").write_text(
    json.dumps(coeficientes, indent=2, ensure_ascii=False), encoding="utf-8"
)
tabla_modelos.to_csv(CARPETA_RESULTADOS / "tabla_modelos.csv", index=False)
tabla_coef.to_csv(CARPETA_RESULTADOS / "tabla_coeficientes.csv", index=False)
tabla_diag.to_csv(CARPETA_RESULTADOS / "tabla_diagnostico_numerico.csv", index=False)
tabla_rmse.to_csv(CARPETA_RESULTADOS / "tabla_rmse.csv", index=False)

# ---- Gráfica 1: sesgo y varianza ----
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(resumen_modelos))
ax.plot(x, resumen_modelos["RMSE_entrenamiento_C"], "o-", label="RMSE de entrenamiento")
ax.plot(x, resumen_modelos["RMSE_LOO_C"], "s-", label="RMSE de validación cruzada (LOO)")
ax.set_xticks(x, [f"{e}\n({p} par.)" for e, p in
                  zip(resumen_modelos["estructura"], resumen_modelos["num_parametros"])], fontsize=8)
ax.set_yscale("log")
ax.set_ylabel("RMSE (°C), promedio de canales")
ax.set_title("E1 - Selección de estructura: sesgo vs varianza - SIMULADO")
ax.grid(True, which="both", alpha=0.4)
ax.legend()
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "sesgo_varianza.png", dpi=120)

# ---- Gráfica 2: residuos e intervalo de predicción por canal ----
fig, ejes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
adc_malla = np.linspace(1300, 3200, 300)
for ax, c in zip(ejes, CANALES):
    ajuste = ajustes[c]
    y_hat, semiancho = intervalo_prediccion(cal.matriz_diseno(adc_malla, ESTRUCTURA), ajuste)
    t_malla = cal.respuesta_a_temperatura(y_hat, ESTRUCTURA)
    banda_a = cal.respuesta_a_temperatura(y_hat - semiancho, ESTRUCTURA) - t_malla
    banda_b = cal.respuesta_a_temperatura(y_hat + semiancho, ESTRUCTURA) - t_malla
    ax.fill_between(t_malla, banda_a, banda_b, alpha=0.2, label="Intervalo de predicción 95 %")
    for datos, marcador, nombre in [(calib, "o", "Calibración"), (prueba, "x", "Prueba")]:
        t_hat = cal.predecir(datos[f"adc_{c}"].to_numpy(), ESTRUCTURA, ajuste["theta"])
        ax.plot(datos["T_ref_C"], datos["T_ref_C"] - t_hat, marcador, label=nombre)
    ax.axhline(0, color="k", lw=0.8)
    ax.axvspan(0, 10, color="tab:green", alpha=0.06)
    ax.set_title(f"Canal {c}")
    ax.set_xlabel("T de referencia (°C)")
    ax.grid(True, alpha=0.4)
ejes[0].set_ylabel("T_ref − T_estimada (°C)")
ejes[0].legend(fontsize=8)
fig.suptitle(f"E1 - Residuos de la calibración ({ESTRUCTURA}) - SIMULADO")
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "residuos_calibracion.png", dpi=120)

# ---- Gráfica 3: curvas de calibración ----
fig, ax = plt.subplots(figsize=(9, 5))
for c in CANALES:
    ax.plot(calib[f"adc_{c}"], calib["T_ref_C"], "o", ms=4, label=f"Canal {c} - calibración")
    ax.plot(adc_malla, cal.predecir(adc_malla, ESTRUCTURA, ajustes[c]["theta"]), lw=1)
ax.plot(prueba["adc_1"], prueba["T_ref_C"], "kx", label="Puntos de prueba (canal 1)")
ax.set_xlabel("Cuenta ADC promedio del escalón")
ax.set_ylabel("Temperatura de referencia (°C)")
ax.set_title(f"E1 - Curvas de calibración ({ESTRUCTURA}) - SIMULADO")
ax.grid(True, alpha=0.4)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "curvas_calibracion.png", dpi=120)

# ---- Resumen en Markdown ----


def a_markdown(df, formato="{:.4g}"):
    columnas = list(df.columns)
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    for _, fila in df.iterrows():
        celdas = [formato.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in fila]
        lineas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(lineas)


ruido_adc_medio = float(np.mean([puntos[f"sd_adc_{c}"].mean() for c in CANALES]))
cumple_todo = bool(tabla_rmse["cumple_0_45"].all() and tabla_rmse["cumple_0_10"].all())

resumen = f"""# Resultados E1 — Calibración (R4–R7)

> Generado por `E1_calibracion/calibracion.py`. Datos **SIMULADOS**.

## R4 — Datos

- {len(calib)} puntos de calibración y {len(prueba)} de prueba
  ({int((calib['T_ref_C'] <= 10).sum())} y {int((prueba['T_ref_C'] <= 10).sum())} en 0–10 °C),
  rango {puntos['T_ref_C'].min():.1f}–{puntos['T_ref_C'].max():.1f} °C.
- Cada punto es el promedio de {int(crudos.groupby('punto').size().iloc[0])} lecturas ADC
  (desviación estándar típica dentro del escalón: {ruido_adc_medio:.2f} cuentas).
- Referencia: {referencia['instrumento']}; resolución {referencia['resolucion_C']} °C,
  exactitud ±{referencia['exactitud_C']} °C → u = {U_REF} °C (tipo B, distribuciones
  rectangulares). Fuente: {referencia['fuente']}

## R5 — Estructuras y selección

{chr(10).join(f"- **{e}**: {i['ecuacion']} ({i['num_parametros']} parámetros)" for e, i in cal.ESTRUCTURAS.items())}

Criterio de generalización: RMSE de validación cruzada dejando uno fuera (LOO),
calculado solo con los puntos de calibración y promediado en los 3 canales.

{a_markdown(resumen_modelos)}

- El RMSE de **entrenamiento** baja siempre al agregar parámetros (menos sesgo).
- El RMSE **LOO** deja de mejorar (o empeora) cuando el modelo empieza a ajustar
  ruido: ahí domina la varianza.
- Regla: la estructura más simple con RMSE_LOO ≤ {TOLERANCIA_PARSIMONIA} × mínimo.
  **Seleccionada: {ESTRUCTURA}** ({cal.ESTRUCTURAS[ESTRUCTURA]['ecuacion']}).

Detalle por canal: `tabla_modelos.csv`. Gráfica: `sesgo_varianza.png`.

## R6 — Ajuste por canal (QR propio)

Criterio: mínimos cuadrados en la variable y = {"T" if cal.ESTRUCTURAS[ESTRUCTURA]['espacio'] == 'T' else "1/T_K"}.
Coeficientes ± error estándar (cov = s²·(XᵀX)⁻¹) e IC 95 % con t de Student:

{a_markdown(tabla_coef, "{:.6g}")}

Condiciones de optimalidad (∇J = −2Xᵀr ≈ 0; ∇²J = 2XᵀX con autovalores > 0 → mínimo
global único) y confiabilidad numérica (número de condición y diferencia relativa
entre QR, ecuaciones normales, SVD y `numpy.linalg.lstsq`, esta última **solo como
contraste con una función de librería**):

{a_markdown(tabla_diag, "{:.3e}")}

Intervalo de predicción al 95 % de una nueva lectura:
ŷ ± t(0,975; gl)·s·√(1 + x₀ᵀ(XᵀX)⁻¹x₀), transformado a °C. Semiancho medio y cobertura
en los puntos de prueba en la tabla de R7; banda completa en `residuos_calibracion.png`.

## R7 — Exactitud en los puntos de prueba

{a_markdown(tabla_rmse)}

Metas: RMSE ≤ {META_RMSE_TOTAL} °C en 0–45 °C y ≤ {META_RMSE_0_10} °C en 0–10 °C.
**{"Se cumplen en los 3 canales." if cumple_todo else "NO se cumplen en todos los canales: ver análisis del error."}**

Análisis del error: RMSE² = sesgo² + varianza. El error de prueba incluye el error
del propio termómetro de referencia (u = {U_REF} °C), que es un piso: ningún modelo
puede tener un RMSE de prueba mucho menor que ese valor. La resolución del ADC
(≈ 0,024 °C/cuenta, ver R1) y el ruido promediado en {int(crudos.groupby('punto').size().iloc[0])} muestras
aportan mucho menos.
"""
(CARPETA_RESULTADOS / "resumen_E1.md").write_text(resumen, encoding="utf-8")

print(f"\nR7: {'CUMPLE' if cumple_todo else 'NO CUMPLE'} las metas en todos los canales")
print(f"Generado en {CARPETA_RESULTADOS.relative_to(RAIZ_REPO)}: coeficientes_calibracion.json, "
      "tabla_modelos.csv, tabla_coeficientes.csv, tabla_diagnostico_numerico.csv, tabla_rmse.csv, "
      "resumen_E1.md, sesgo_varianza.png, residuos_calibracion.png, curvas_calibracion.png")
