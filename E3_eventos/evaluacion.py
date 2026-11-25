"""
R13 - Evaluación del detector de E3 (datos SIMULADOS).

Carga resultados/parametros_detector.json (generado por detector.py con SOLO los
datos de entrenamiento) y lo aplica SIN REAJUSTAR NADA a:
  - validacion.csv : falsas alarmas por hora (meta ≤ 1/h)
  - prueba.csv     : retardo de detección de cada evento de tabla_eventos.csv
                     (metas: 100 % detectados, ≤ 60 s aperturas, ≤ 20 s desconexiones)
NO lee VERDAD_NO_USAR.json.

Definiciones (Sección 8 del enunciado)
--------------------------------------
- Retardo: desde el inicio real del evento hasta la primera alarma.
- Un evento se considera detectado si hay alarma entre su inicio y 60 s después
  de su fin.
- Falsa alarma: una alarma que se ACTIVA (paso de "sin alarma" a "alarma") sin
  ningún evento en curso y fuera de los 60 s posteriores al fin del último evento.

Uso:  python E3_eventos/evaluacion.py     (antes: python E3_eventos/detector.py)
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
from E3_eventos import detector as det  # noqa: E402

MARGEN_POSTERIOR_S = 60          # Sección 8: 60 s después del fin del evento
META_FALSAS_POR_HORA = 1.0
META_RETARDO_S = {"apertura": 60, "desconexion": 20}
COLORES_EVENTO = {"apertura": "tab:orange", "desconexion": "tab:red"}


def correr_detector(nombre, parametros, coeficientes):
    """Aplica el detector ya entrenado a una sesión. Devuelve una tabla por muestra."""
    tabla = pd.read_csv(det.CARPETA_DATOS / f"{nombre}.csv")
    x, desconectado = det.preparar_datos(tabla, coeficientes, parametros["ventana_suavizado_s"])
    t2, q = det.estadisticos(x, parametros)
    anomala = det.muestras_anomalas(t2, q, desconectado, parametros)
    alarma = det.aplicar_persistencia(anomala, parametros["K_persistencia"])
    return pd.DataFrame({"t_s": tabla["t_s"], "T2": t2, "Q": q,
                         "desconectado": desconectado, "alarma": alarma})


def inicios_de_alarma(resultado):
    """Instantes en que la alarma pasa de apagada a encendida."""
    alarma = resultado["alarma"].to_numpy()
    previa = np.concatenate([[False], alarma[:-1]])
    return resultado["t_s"].to_numpy()[alarma & ~previa]


def es_falsa(t, eventos):
    """True si en el instante t no hay evento en curso ni en sus 60 s posteriores."""
    for _, ev in eventos.iterrows():
        if ev["t_inicio_s"] <= t < ev["t_fin_s"] + MARGEN_POSTERIOR_S:
            return False
    return True


def causa_falsa(ti, resultado, eventos, parametros):
    """
    Diagnóstico (solo para explicar, no cambia nada): qué estadístico disparó la
    falsa alarma y si ocurrió poco después de un evento (cola de recuperación).
    """
    fila = resultado[resultado["t_s"] == ti].iloc[0]
    estadistico = "T²" if fila["T2"] > parametros["umbral_T2"] else "Q"
    tras_evento = any(0 <= ti - ev["t_fin_s"] < 4 * MARGEN_POSTERIOR_S for _, ev in eventos.iterrows())
    return estadistico, tras_evento


def demostrar_solo_entrenamiento(parametros, coeficientes):
    """
    R12: demostración NUMÉRICA de que μ, s y los umbrales salen solo de entrenamiento.
    Se recalcula cada valor con cada sesión por separado: solo la de entrenamiento
    reproduce lo guardado en el JSON (diferencia ≈ 0). Esto NO cambia el detector.
    """
    filas = []
    for nombre in ["entrenamiento", "validacion", "prueba"]:
        tabla = pd.read_csv(det.CARPETA_DATOS / f"{nombre}.csv")
        x, _ = det.preparar_datos(tabla, coeficientes, parametros["ventana_suavizado_s"])
        x = x[~np.isnan(x).any(axis=1)]
        t2, q = det.estadisticos(x, parametros)
        filas.append({
            "sesion": nombre,
            "dif_mu_max": float(np.max(np.abs(x.mean(axis=0) - parametros["mu"]))),
            "dif_s_max": float(np.max(np.abs(x.std(axis=0, ddof=1) - parametros["s"]))),
            "dif_umbral_T2": abs(float(np.percentile(t2, parametros["percentil_umbral"])) - parametros["umbral_T2"]),
            "dif_umbral_Q": abs(float(np.percentile(q, parametros["percentil_umbral"])) - parametros["umbral_Q"]),
        })
    return pd.DataFrame(filas)


def main():
    parametros = json.loads(det.RUTA_PARAMETROS.read_text(encoding="utf-8"))
    coeficientes = cal.cargar_coeficientes()
    eventos = pd.read_csv(det.CARPETA_DATOS / "tabla_eventos.csv")

    # ---------------- R12: demostración de que solo se usó entrenamiento ----------------
    assert parametros["archivos_leidos"] == ["E3_eventos/datos/entrenamiento.csv"]
    demo = demostrar_solo_entrenamiento(parametros, coeficientes)
    print("========== R12: ¿DE QUÉ SESIÓN SALEN LOS PARÁMETROS? ==========")
    print("(diferencia entre lo guardado en el JSON y lo recalculado con cada sesión)")
    print(demo.to_string(index=False, float_format=lambda v: f"{v:.2e}"))
    print()

    # ---------------- Validación: falsas alarmas ----------------
    val = correr_detector("validacion", parametros, coeficientes)
    horas_val = len(val) * 1.0 / 3600          # Ts = 1 s
    falsas_val = len(inicios_de_alarma(val))   # en validación no hay eventos
    tasa_val = falsas_val / horas_val
    cumple_val = tasa_val <= META_FALSAS_POR_HORA
    print("========== R13: VALIDACIÓN (operación normal) ==========")
    print(f"Duración: {60 * horas_val:.0f} min   Alarmas: {falsas_val}   "
          f"Falsas alarmas por hora: {tasa_val:.2f}  (meta ≤ {META_FALSAS_POR_HORA:.0f}/h) -> "
          f"{'CUMPLE' if cumple_val else 'NO CUMPLE'}")

    # ---------------- Prueba: retardo de cada evento ----------------
    pru = correr_detector("prueba", parametros, coeficientes)
    t = pru["t_s"].to_numpy()
    alarma = pru["alarma"].to_numpy()
    filas = []
    for _, ev in eventos.iterrows():
        ventana = (t >= ev["t_inicio_s"]) & (t < ev["t_fin_s"] + MARGEN_POSTERIOR_S) & alarma
        detectado = bool(ventana.any())
        retardo = float(t[ventana][0] - ev["t_inicio_s"]) if detectado else np.nan
        meta = META_RETARDO_S[ev["tipo"]]
        filas.append({
            "evento": ev["tipo"],
            "sensor": "" if pd.isna(ev["sensor"]) else int(ev["sensor"]),
            "inicio [s]": int(ev["t_inicio_s"]),
            "fin [s]": int(ev["t_fin_s"]),
            "detectado": "sí" if detectado else "no",
            "retardo [s]": retardo,
            "meta [s]": meta,
            "cumple": "sí" if detectado and retardo <= meta else "no",
        })
    tabla_retardo = pd.DataFrame(filas)
    falsas_pru = [int(ti) for ti in inicios_de_alarma(pru) if es_falsa(ti, eventos)]
    causas = [causa_falsa(ti, pru, eventos, parametros) for ti in falsas_pru]
    diagnostico = {
        "por_T2": sum(c[0] == "T²" for c in causas),
        "por_Q": sum(c[0] == "Q" for c in causas),
        "Q_tras_evento": sum(c[0] == "Q" and c[1] for c in causas),
    }
    # Retardo "contaminado": la alarma ya estaba encendida cuando empezó el evento.
    tabla_retardo["alarma previa"] = [
        "sí" if bool(pru.loc[pru["t_s"] == ev["t_inicio_s"] - 1, "alarma"].any()) else "no"
        for _, ev in eventos.iterrows()]
    tasa_pru = len(falsas_pru) / (len(pru) / 3600)
    porcentaje = 100 * (tabla_retardo["detectado"] == "sí").mean()

    print("\n========== R13: PRUEBA (eventos) ==========")
    print(tabla_retardo.to_string(index=False))
    print(f"Detectados: {porcentaje:.0f} %   Falsas alarmas en prueba: {len(falsas_pru)} "
          f"({tasa_pru:.2f}/h)" + (f" en t = {falsas_pru} s" if falsas_pru else ""))
    if falsas_pru:
        print(f"  Causa: {diagnostico['por_T2']} por T², {diagnostico['por_Q']} por Q "
              f"({diagnostico['Q_tras_evento']} de ellas en los 4 min siguientes a un evento)")
    cumple_todo = cumple_val and (tabla_retardo["cumple"] == "sí").all()
    print("R13: " + ("CUMPLE las metas (falsas alarmas en validación y retardos en prueba)"
                     if cumple_todo else "NO cumple alguna meta (ver resumen)"))
    if falsas_pru:
        print(f"  ADVERTENCIA: en prueba hubo {tasa_pru:.1f} falsas alarmas/h, muy por encima de 1/h "
              "(ver la sección 'Desviaciones' del resumen).")

    grafica_prueba(pru, eventos, parametros)
    escribir_resumen(parametros, demo, horas_val, falsas_val, tasa_val, cumple_val,
                     tabla_retardo, porcentaje, falsas_pru, tasa_pru, cumple_todo, diagnostico)
    print("\nGuardado: E3_eventos/resultados/deteccion_prueba.png, resumen_E3.md")


def grafica_prueba(pru, eventos, parametros):
    fig, ejes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    t_min = pru["t_s"] / 60
    for eje, columna, umbral in [(ejes[0], "T2", parametros["umbral_T2"]),
                                 (ejes[1], "Q", parametros["umbral_Q"])]:
        eje.plot(t_min, pru[columna], lw=0.8, color="tab:blue", label=columna)
        eje.axhline(umbral, color="k", ls="--", lw=1, label=f"umbral {columna} = {umbral:.3g}")
        eje.set_yscale("log")
        eje.set_ylabel(columna)
        eje.legend(loc="upper left", fontsize=8)
    ejes[2].step(t_min, pru["alarma"].astype(int), where="post", color="tab:red", label="alarma")
    ejes[2].step(t_min, 0.5 * pru["desconectado"].astype(int), where="post",
                 color="gray", label="canal desconectado (×0,5)")
    ejes[2].set_yticks([0, 1])
    ejes[2].set_yticklabels(["no", "sí"])
    ejes[2].set_xlabel("tiempo [min]")
    ejes[2].legend(loc="upper left", fontsize=8)
    for eje in ejes:
        for _, ev in eventos.iterrows():
            eje.axvspan(ev["t_inicio_s"] / 60, ev["t_fin_s"] / 60,
                        color=COLORES_EVENTO[ev["tipo"]], alpha=0.3)
    ejes[0].set_title("Detector PCA en la sesión de prueba (naranja: apertura, rojo: desconexión) — SIMULADO")
    fig.tight_layout()
    fig.savefig(det.CARPETA_RESULTADOS / "deteccion_prueba.png", dpi=120)
    plt.close(fig)


def escribir_resumen(p, demo, horas_val, falsas_val, tasa_val, cumple_val,
                     tabla_retardo, porcentaje, falsas_pru, tasa_pru, cumple_todo, diagnostico):
    r14 = p["R14"]
    filas_demo = "\n".join(
        f"| {d['sesion']} | {d['dif_mu_max']:.1e} | {d['dif_s_max']:.1e} | "
        f"{d['dif_umbral_T2']:.1e} | {d['dif_umbral_Q']:.1e} |"
        for d in demo.to_dict("records"))
    lineas_aut = "\n".join(
        f"| {j + 1} | {lam:.4f} | {100 * lam / sum(p['autovalores']):.2f} |"
        for j, lam in enumerate(p["autovalores"]))
    filas = []
    for f in tabla_retardo.to_dict("records"):
        retardo = "—" if np.isnan(f["retardo [s]"]) else f"{f['retardo [s]']:.0f}"
        filas.append(f"| {f['evento']} | {f['sensor']} | {f['inicio [s]']}–{f['fin [s]']} | "
                     f"{f['detectado']} | {retardo} | ≤ {f['meta [s]']} | {f['cumple']} | {f['alarma previa']} |")
    filas_ret = "\n".join(filas)
    desviaciones = ""
    if falsas_pru:
        previas = tabla_retardo[tabla_retardo["alarma previa"] == "sí"]
        nota_previa = ""
        if len(previas):
            nota_previa = (
                "\n- **Retardos de 0 s no son reales**: en "
                + ", ".join(f"{r['evento']} (t = {r['inicio [s]']} s)" for r in previas.to_dict("records"))
                + " la alarma ya estaba encendida por una falsa alarma cuando empezó el evento. "
                f"Sin ella, una desconexión se detecta en K − 1 = {p['K_persistencia'] - 1} s "
                "(primera lectura en 4095 + K muestras seguidas).")
        desviaciones = f"""
## Desviaciones (se reportan, NO se corrigieron mirando validación ni prueba)

En la sesión de prueba hubo **{len(falsas_pru)} falsas alarmas ({tasa_pru:.1f}/h)**, aunque en
validación hubo {falsas_val}. Diagnóstico de cada una: {diagnostico['por_T2']} por T² y
{diagnostico['por_Q']} por Q ({diagnostico['Q_tras_evento']} de estas en los 4 min siguientes al fin de un evento).

- **Por T²**: con k = 1, T² mide solo la oscilación común de la nevera, que es comportamiento
  normal. El umbral (percentil {p['percentil_umbral']}) quedó justo en la cresta de esa oscilación
  porque el entrenamiento (30 min) contiene un único ciclo de 30 min; la prueba dura 70 min y
  cualquier cresta un poco más alta lo supera. El entrenamiento es demasiado corto para
  representar toda la variación normal.
- **Por Q tras un evento**: después de cerrar la tapa, el aire junto al sensor 1 vuelve a la
  temperatura del contenido con τ ≈ 2 min. Pasado el margen de 60 s de la Sección 8 todavía
  queda una diferencia entre sensores que rompe el patrón, y Q la ve. Físicamente el sistema
  aún no ha vuelto a la normalidad, pero la definición la cuenta como falsa alarma.
- **Por Q en el resto ({diagnostico['por_Q'] - diagnostico['Q_tras_evento']})**: un percentil {p['percentil_umbral']} deja, por definición,
  un {100 - p['percentil_umbral']:.1f} % de muestras normales por encima. Como el promedio móvil hace que
  las muestras vecinas se parezcan, esas superaciones vienen en grupos y la persistencia
  K = {p['K_persistencia']} no alcanza a filtrarlas.{nota_previa}

Posibles mejoras (habría que justificarlas con entrenamiento o con criterios físicos, no
ajustándolas a la prueba): entrenar con una sesión normal más larga (varios ciclos de la nevera),
usar un umbral con margen sobre el máximo de entrenamiento, o no evaluar T² cuando k = 1
y solo representa la oscilación común.
"""
    texto = f"""# Resumen E3 — Detector de anomalías con PCA (R12–R14)

Todos los datos son **SIMULADOS**. Los parámetros del detector se fijaron solo con
`entrenamiento.csv` (`detector.py`); validación y prueba solo se evaluaron
(`evaluacion.py`), sin reajustar nada.

## R12 — Detector

### Formulación matemática

Cada muestra n da un vector de 3 temperaturas calibradas (E1) y suavizadas con un
promedio móvil de V = {p['ventana_suavizado_s']} muestras:

    x[n] = (1/V) · Σ_(j=0..V−1) T[n−j]          (vector de 3 elementos, °C)

**Entrenamiento** (N = {p['n_muestras_usadas']} muestras de `entrenamiento.csv`):

    μ = (1/N) Σ x[n]                    media de cada sensor
    s = desviación estándar de cada sensor
    z[n] = (x[n] − μ) / s               (elemento a elemento)
    R = ZᵀZ / (N − 1)                   matriz 3 × 3 (Z: las N filas z[n])
    R·pᵢ = λᵢ·pᵢ                        autovalores λ₁ ≥ λ₂ ≥ λ₃ y autovectores pᵢ
    P = [p₁ … p_k]                      las k componentes retenidas (3 × k)

**Estadísticos de una muestra nueva** (z con μ y s de entrenamiento):

    t = Pᵀ·z                            coordenadas de z en las componentes retenidas
    T² = Σ_(i=1..k) tᵢ² / λᵢ            distancia DENTRO del patrón normal
    Q  = ‖z − P·Pᵀ·z‖²                  lo que el patrón normal NO explica

**Regla de decisión**:

    anómala[n] = (T²[n] > umbral_T²) o (Q[n] > umbral_Q) o (algún ADC ≥ 4090)
    alarma[n]  = anómala[n] y anómala[n−1] y … y anómala[n−K+1]      (K = {p['K_persistencia']})

**Criterio para k**: el menor k con Σ_(i≤k) λᵢ / Σλᵢ ≥ 0,90.

**Criterio para los umbrales**: percentil {p['percentil_umbral']} de T² y de Q en entrenamiento
(se acepta que el {100 - p['percentil_umbral']:.1f} % de las muestras normales lo supere; la
persistencia K filtra los picos aislados).

### Parámetros

| Parámetro | Valor | Cómo se fijó |
|---|---|---|
| Suavizado | promedio móvil causal de {p['ventana_suavizado_s']} s | a priori: baja el ruido ≈ 3 veces y es 3 veces más corto que una apertura |
| Componentes k | {p['k']} | {p['criterio_k']} (fijado a priori) |
| Umbral T² | {p['umbral_T2']:.4f} | percentil {p['percentil_umbral']} en entrenamiento |
| Umbral Q | {p['umbral_Q']:.4f} | percentil {p['percentil_umbral']} en entrenamiento |
| Persistencia K | {p['K_persistencia']} muestras | a priori |
| Desconexión | ADC ≥ 4090 → muestra anómala directamente | regla física, sin PCA |

Autovalores de la matriz de correlación (gráfica de codo en `codo_pca.png`):

| componente | λ | varianza [%] |
|---|---|---|
{lineas_aut}

### Demostración de que solo se usó entrenamiento

1. `detector.py` lee un único archivo de datos: `{p['archivos_leidos'][0]}`
   (queda registrado en `parametros_detector.json`, campo `archivos_leidos`), con
   N = {p['n_muestras_usadas']} muestras, t = {p['intervalo_t_s_usado'][0]:.0f}–{p['intervalo_t_s_usado'][1]:.0f} s.
2. `evaluacion.py` no calcula ningún parámetro: solo carga el JSON y lo aplica.
3. Comprobación numérica: se recalculan μ, s y los umbrales con cada sesión por separado.
   Solo entrenamiento reproduce los valores del JSON (diferencia ≈ 0, error de redondeo);
   con validación o prueba saldrían valores distintos.

| sesión | dif. máx. μ [°C] | dif. máx. s [°C] | dif. umbral T² | dif. umbral Q |
|---|---|---|---|---|
{filas_demo}

## R13 — Desempeño

**Validación** ({60 * horas_val:.0f} min de operación normal): {falsas_val} alarma(s) →
**{tasa_val:.2f} falsas alarmas/h** (meta ≤ 1/h) → **{'CUMPLE' if cumple_val else 'NO CUMPLE'}**.

**Prueba**:

| evento | sensor | intervalo [s] | detectado | retardo [s] | meta | cumple | alarma ya encendida |
|---|---|---|---|---|---|---|---|
{filas_ret}

Detectados: **{porcentaje:.0f} %**. Falsas alarmas en prueba: {len(falsas_pru)} ({tasa_pru:.2f}/h).
Metas de R13 (falsas alarmas en validación, 100 % detectados y retardos):
**{'CUMPLEN' if cumple_todo else 'NO se cumple alguna'}**. Gráfica: `deteccion_prueba.png`.
{desviaciones}
## R14 — Compresión

| Medida | Fórmula | Valor | Interpretación |
|---|---|---|---|
| (i) Información conservada | Σλ(1..k) / Σλ | {r14['informacion_conservada']:.4f} | con {p['k']} de 3 componentes se conserva el {100 * r14['informacion_conservada']:.1f} % de la variación |
| (ii) Factor de compresión | 3 / k | {r14['factor_compresion']:.2f} | cada muestra se guarda con {p['k']} número(s) en vez de 3 |
| (iii) Error de reconstrucción | promedio de Q = promedio de ‖z − P·Pᵀ·z‖² | {r14['error_reconstruccion_Q_medio']:.4f} | de una varianza total de 3 (en z) se pierde ≈ {100 * r14['error_reconstruccion_Q_medio'] / 3:.1f} % |
"""
    (det.CARPETA_RESULTADOS / "resumen_E3.md").write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
