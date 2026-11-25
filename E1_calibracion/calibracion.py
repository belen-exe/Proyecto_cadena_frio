"""
R5, R6, R7 - Calibración ADC -> temperatura con álgebra matricial propia.

Pasos
-----
1. Promedia las N lecturas ADC de cada escalón (reduce el ruido del ADC).
2. R5: ajusta 3 estructuras de complejidad creciente (comun/calibracion.py) SOLO con
   los puntos de calibración y elige una con un criterio de generalización:
   el RMSE de validación cruzada (dejando un punto fuera cada vez), promediado en
   los canales. Regla de parsimonia: la estructura más simple cuyo RMSE de
   validación cruzada no supere en más de
   un 5 % al mínimo.
3. R6: con la estructura elegida, por canal: coeficientes ± error estándar,
   intervalo de predicción al 95 %, condiciones de optimalidad (gradiente nulo y
   hessiano definido positivo) y confiabilidad numérica (número de condición de X).
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
from comun.estadistica import ajustar_mco, intervalo_prediccion, rmse  # noqa: E402

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
U_REF = referencia["incertidumbre_C"]

puntos = crudos.groupby("punto").agg(
    tipo=("tipo", "first"),
    T_ref_C=("T_ref_C", "first"),
    **{f"adc_{c}": (f"adc_{c}", "mean") for c in CANALES},
    **{f"sd_adc_{c}": (f"adc_{c}", "std") for c in CANALES},
).reset_index()

calib = puntos[puntos["tipo"] == "calibracion"].reset_index(drop=True)
prueba = puntos[puntos["tipo"] == "prueba"].reset_index(drop=True)

print(f"Puntos de calibración: {len(calib)}  |  puntos de prueba: {len(prueba)}")
print(f"Incertidumbre de la referencia: ±{U_REF} C ({referencia['instrumento']})")

# ==========================================
# 2. R5 - COMPARACIÓN DE ESTRUCTURAS (solo datos de calibración)
# ==========================================


def rmse_validacion_cruzada(adc, temperatura, estructura):
    """
    RMSE [°C] de validación cruzada: con n puntos se hacen n rondas; en cada una
    se ajusta el modelo con n − 1 puntos y se predice el punto que quedó fuera.
    Mide qué tan bien predice el modelo puntos que NO usó para ajustarse.
    """
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
            "RMSE_validacion_cruzada_C": rmse_validacion_cruzada(adc, temp, estructura),
            "RMSE_prueba_C (informativo)": rmse(prueba["T_ref_C"] - t_hat_prueba),
            "cond_X": ajuste["diagnostico"]["numero_condicion_X"],
        })

tabla_modelos = pd.DataFrame(filas_modelos)
resumen_modelos = tabla_modelos.groupby("estructura", sort=False).agg(
    num_parametros=("num_parametros", "first"),
    RMSE_entrenamiento_C=("RMSE_entrenamiento_C", "mean"),
    RMSE_validacion_cruzada_C=("RMSE_validacion_cruzada_C", "mean"),
).reset_index()

rmse_vc_min = resumen_modelos["RMSE_validacion_cruzada_C"].min()
candidatas = resumen_modelos[resumen_modelos["RMSE_validacion_cruzada_C"] <= TOLERANCIA_PARSIMONIA * rmse_vc_min]
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
filas_coef, filas_diag, filas_0_45, filas_0_10, filas_ip = [], [], [], [], []
ajustes = {}


def metricas_error(canal, error, meta):
    """Fila de la tabla de R7 para un canal y un rango de temperatura."""
    return {
        "canal": canal,
        "n puntos": len(error),
        "RMSE [°C]": rmse(error),
        "sesgo [°C]": float(np.mean(error)),
        "desv. est. [°C]": float(np.std(error)),
        "error máx. [°C]": float(np.max(np.abs(error))),
        "meta [°C]": meta,
        "cumple": "sí" if rmse(error) <= meta else "NO",
    }


for c in CANALES:
    adc = calib[f"adc_{c}"].to_numpy()
    temp = calib["T_ref_C"].to_numpy()
    X = cal.matriz_diseno(adc, ESTRUCTURA)
    y = cal.objetivo(temp, ESTRUCTURA)
    ajuste = ajustar_mco(X, y)
    ajustes[c] = ajuste

    coeficientes["canales"][str(c)] = {
        "theta": ajuste["theta"].tolist(),
        "error_estandar": ajuste["error_estandar"].tolist(),
        "cov": ajuste["cov"].tolist(),
        "XtX_inv": ajuste["XtX_inv"].tolist(),
        "s": ajuste["s"],
        "gl": ajuste["gl"],
    }

    for j, (theta, ee) in enumerate(zip(ajuste["theta"], ajuste["error_estandar"])):
        filas_coef.append({
            "canal": c, "parametro": f"θ{j}", "valor": theta, "error_estandar": ee,
        })

    d = ajuste["diagnostico"]
    filas_diag.append({
        "canal": c,
        "gradiente relativo": d["gradiente_relativo"],
        "λ mín. hessiano": d["autovalor_min_hessiano"],
        "cond(X)": d["numero_condicion_X"],
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
    filas_0_45.append(metricas_error(c, error, META_RMSE_TOTAL))
    filas_0_10.append(metricas_error(c, error[zona], META_RMSE_0_10))
    filas_ip.append({
        "canal": c,
        "semiancho medio [°C]": float(np.mean(np.abs(lim_b - lim_a) / 2)),
        "puntos dentro": f"{int(dentro_ip.sum())} de {len(dentro_ip)}",
        "cobertura [%]": int(round(100 * float(dentro_ip.mean()))),
    })

tabla_coef = pd.DataFrame(filas_coef)
tabla_diag = pd.DataFrame(filas_diag)
tabla_0_45 = pd.DataFrame(filas_0_45)
tabla_0_10 = pd.DataFrame(filas_0_10)
tabla_ip = pd.DataFrame(filas_ip)

print("\n========== R6: COEFICIENTES ==========")
print(tabla_coef[["canal", "parametro", "valor", "error_estandar"]]
      .to_string(index=False, float_format=lambda v: f"{v:.6g}"))
print("\n========== R6: OPTIMALIDAD Y CONFIABILIDAD NUMÉRICA ==========")
print(tabla_diag.to_string(index=False, float_format=lambda v: f"{v:.3e}"))
print("\n========== R6: INTERVALO DE PREDICCIÓN 95 % (puntos de prueba) ==========")
print(tabla_ip.round(4).to_string(index=False))
print("\n========== R7: PUNTOS DE PRUEBA, TODO EL RANGO 0-45 °C ==========")
print(tabla_0_45.round(4).to_string(index=False))
print("\n========== R7: PUNTOS DE PRUEBA, ZONA CRÍTICA 0-10 °C ==========")
print(tabla_0_10.round(4).to_string(index=False))

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
tabla_0_45.to_csv(CARPETA_RESULTADOS / "tabla_rmse_0_45C.csv", index=False)
tabla_0_10.to_csv(CARPETA_RESULTADOS / "tabla_rmse_0_10C.csv", index=False)
tabla_ip.to_csv(CARPETA_RESULTADOS / "tabla_intervalo_prediccion.csv", index=False)

# ---- Gráfica 1: sesgo y varianza ----
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(resumen_modelos))
ax.plot(x, resumen_modelos["RMSE_entrenamiento_C"], "o-", label="RMSE de entrenamiento")
ax.plot(x, resumen_modelos["RMSE_validacion_cruzada_C"], "s-", label="RMSE de validación cruzada")
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
    for _, fila in df.astype(object).iterrows():
        celdas = [formato.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in fila]
        lineas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(lineas)


ruido_adc_medio = float(np.mean([puntos[f"sd_adc_{c}"].mean() for c in CANALES]))
cumple_todo = bool((tabla_0_45["cumple"] == "sí").all() and (tabla_0_10["cumple"] == "sí").all())

resumen = f"""# Resultados E1 — Calibración (R4–R7)

> Generado por `E1_calibracion/calibracion.py`. Datos **SIMULADOS**.

## R4 — Datos

- {len(calib)} puntos de calibración y {len(prueba)} de prueba
  ({int((calib['T_ref_C'] <= 10).sum())} y {int((prueba['T_ref_C'] <= 10).sum())} en 0–10 °C),
  rango {puntos['T_ref_C'].min():.1f}–{puntos['T_ref_C'].max():.1f} °C.
- Cada punto es el promedio de {int(crudos.groupby('punto').size().iloc[0])} lecturas ADC
  (desviación estándar típica dentro del escalón: {ruido_adc_medio:.2f} cuentas).
- Referencia: {referencia['instrumento']}; resolución {referencia['resolucion_C']} °C,
  incertidumbre = exactitud de la ficha técnica = ±{U_REF} °C. Fuente: {referencia['fuente']}

## R5 — Estructuras y selección

{chr(10).join(f"- **{e}**: {i['ecuacion']} ({i['num_parametros']} parámetros)" for e, i in cal.ESTRUCTURAS.items())}

Criterio de generalización: RMSE de **validación cruzada**, calculado solo con los
puntos de calibración y promediado en los 3 canales. Con los 28 puntos se hacen 28
rondas: en cada una se ajusta con 27 puntos y se predice el que quedó fuera.

{a_markdown(resumen_modelos)}

- El RMSE de **entrenamiento** baja siempre al agregar parámetros (menos sesgo).
- El RMSE de **validación cruzada** deja de mejorar (o empeora) cuando el modelo
  empieza a ajustar ruido: ahí domina la varianza.
- Regla: la estructura más simple con RMSE de validación cruzada ≤ {TOLERANCIA_PARSIMONIA} × mínimo.
  **Seleccionada: {ESTRUCTURA}** ({cal.ESTRUCTURAS[ESTRUCTURA]['ecuacion']}).

Detalle por canal: `tabla_modelos.csv`. Gráfica: `sesgo_varianza.png`.

## R6 — Ajuste por canal (ecuaciones normales, implementación propia)

Criterio: mínimos cuadrados en la variable y = {"T" if cal.ESTRUCTURAS[ESTRUCTURA]['espacio'] == 'T' else "1/T_K"}, resuelto con las
ecuaciones normales: **θ = (XᵀX)⁻¹·Xᵀ·y** (matriz de diseño X por canal).
Coeficientes con su incertidumbre (error estándar = raíz de la diagonal de cov = s²·(XᵀX)⁻¹):

{a_markdown(tabla_coef, "{:.6g}")}

- **Gradiente relativo ≈ 0** (∇J = −2Xᵀr): se está en un punto donde J no baja más.
- **λ mín. del hessiano > 0** (∇²J = 2XᵀX): ese punto es un mínimo, y es único.
- **cond(X) pequeño**: la inversa (XᵀX)⁻¹ se calculó sin perder precisión.

{a_markdown(tabla_diag, "{:.3g}")}

**Intervalo de predicción al 95 %** de una nueva lectura:
ŷ ± t·s·√(1 + x₀ᵀ(XᵀX)⁻¹x₀) (t de la tabla t), transformado a °C. Evaluado en los
puntos de prueba; si está bien calculado, cerca del 95 % de ellos deben caer dentro.
Banda completa en `residuos_calibracion.png`.

{a_markdown(tabla_ip, "{:.3f}")}

## R7 — Exactitud en los puntos de prueba

Error de cada punto = T_ref − T_estimada.

**Todo el rango (0–45 °C)**, meta RMSE ≤ {META_RMSE_TOTAL} °C:

{a_markdown(tabla_0_45, "{:.3f}")}

**Zona crítica (0–10 °C)**, meta RMSE ≤ {META_RMSE_0_10} °C:

{a_markdown(tabla_0_10, "{:.3f}")}

**{"Se cumplen las dos metas en los 3 canales." if cumple_todo else "NO se cumplen en todos los canales: ver análisis del error."}**

Análisis del error: RMSE² = sesgo² + desv. est.². El error de prueba incluye el error
del propio termómetro de referencia (±{U_REF} °C), que es un piso: ningún modelo
puede tener un RMSE de prueba mucho menor que ese valor. La resolución del ADC
(≈ 0,024 °C/cuenta, ver R1) y el ruido promediado en {int(crudos.groupby('punto').size().iloc[0])} muestras
aportan mucho menos.
"""
(CARPETA_RESULTADOS / "resumen_E1.md").write_text(resumen, encoding="utf-8")

print(f"\nR7: {'CUMPLE' if cumple_todo else 'NO CUMPLE'} las metas en todos los canales")
print(f"Generado en {CARPETA_RESULTADOS.relative_to(RAIZ_REPO)}: coeficientes_calibracion.json, "
      "tabla_modelos.csv, tabla_coeficientes.csv, tabla_diagnostico_numerico.csv, "
      "tabla_rmse_0_45C.csv, tabla_rmse_0_10C.csv, tabla_intervalo_prediccion.csv, "
      "resumen_E1.md, sesgo_varianza.png, residuos_calibracion.png, curvas_calibracion.png")
