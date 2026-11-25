"""
R12 y R14 - Detector de anomalías con PCA (datos SIMULADOS).

Este script SOLO lee E3_eventos/datos/entrenamiento.csv. Con esos datos fija TODO:
la ventana de suavizado, el número de componentes k, los umbrales y la
persistencia K. Validación y prueba se usan después, en evaluacion.py, sin
reajustar nada. NO lee VERDAD_NO_USAR.json.

Idea del detector
-----------------
En operación normal los tres sensores suben y bajan juntos (la oscilación de la
nevera les llega a todos). El PCA aprende ese patrón "normal". Una apertura de la
tapa calienta mucho al sensor 1 y poco al 3, lo que rompe el patrón; una
desconexión deja el canal en 4095.

  T²: qué tan lejos está la muestra del centro, DENTRO del patrón normal.
  Q : cuánto de la muestra NO se puede explicar con el patrón normal.

Pasos
-----
1. ADC -> °C con la calibración de E1 y promedio móvil de VENTANA_S muestras.
2. PCA a mano: media μ, desviación s, z = (x − μ)/s, R = ZᵀZ/(n−1), eigh(R).
3. k = mínimo número de componentes con varianza acumulada ≥ VARIANZA_OBJETIVO.
4. T² y Q de cada muestra.
5. Umbrales = percentil PERCENTIL_UMBRAL de T² y de Q en entrenamiento.
   Alarma si la muestra es anómala durante K muestras seguidas.
6. Guarda todo en resultados/parametros_detector.json y calcula los números de R14.

Uso:  python E3_eventos/detector.py
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

CARPETA = Path(__file__).resolve().parent
CARPETA_DATOS = CARPETA / "datos"
CARPETA_RESULTADOS = CARPETA / "resultados"
RUTA_PARAMETROS = CARPETA_RESULTADOS / "parametros_detector.json"

CANALES = [1, 2, 3]

# ==========================================
# PARÁMETROS FIJADOS A PRIORI (antes de ver ningún resultado)
# ==========================================

# Ventana del promedio móvil [muestras, con Ts = 1 s]. 10 s porque:
#  - el ruido baja √10 ≈ 3,2 veces (de ≈ 0,095 °C a ≈ 0,03 °C);
#  - una apertura dura 30 s, así que la ventana es 3 veces más corta que el evento
#    y no lo borra; solo agrega ≈ 5 s de retardo (la mitad de la ventana), lejos
#    de la meta de 60 s.
# El promedio es CAUSAL (usa solo la muestra actual y las 9 anteriores), como lo
# haría el ESP32 en tiempo real.
VENTANA_S = 10

# Criterio de k: la menor cantidad de componentes que conserve al menos el 90 %
# de la varianza (valor usual en los libros de PCA).
VARIANZA_OBJETIVO = 0.90

# Umbral: percentil 99,5 de T² y de Q en entrenamiento. Es decir, se acepta que
# solo el 0,5 % de las muestras normales queden por encima.
PERCENTIL_UMBRAL = 99.5

# Persistencia: la alarma se activa si la muestra es anómala K veces seguidas.
# Evita que un solo pico de ruido dispare la alarma.
K_PERSISTENCIA = 3

# ==========================================
# FUNCIONES (también las usa evaluacion.py)
# ==========================================


def preparar_datos(tabla, coeficientes, ventana=VENTANA_S):
    """
    Convierte una sesión (t_s, adc_1..3) en:
      x            matriz n × 3 de temperaturas suavizadas [°C] (NaN si no hay dato)
      desconectado vector n de booleanos: algún canal en el extremo del ADC

    Desconexión (decisión simple): si un ADC llega a ≥ 4090 (o ≤ 5) ese canal no
    tiene una temperatura válida, así que:
      - la muestra se marca directamente como ANÓMALA (no hace falta PCA: un
        sensor desconectado es una falla segura, no una duda estadística);
      - su temperatura queda NaN y en esa muestra no se calculan T² ni Q, porque
        el PCA necesita los tres canales.
    """
    adc = tabla[[f"adc_{c}" for c in CANALES]].to_numpy(dtype=float)
    desconectado = ((adc >= ms.ADC_LIMITE_SUPERIOR) | (adc <= ms.ADC_LIMITE_INFERIOR)).any(axis=1)

    temperatura = np.column_stack([
        cal.adc_a_temperatura_calibrada(adc[:, i], c, coeficientes)
        for i, c in enumerate(CANALES)
    ])

    # Promedio móvil causal. min_periods = ventana: si en la ventana falta algún
    # dato (inicio de la sesión o justo después de una desconexión) el resultado
    # es NaN y esa muestra no se evalúa, en vez de usar un promedio más ruidoso.
    x = (pd.DataFrame(temperatura)
         .rolling(window=ventana, min_periods=ventana).mean()
         .to_numpy())
    return x, desconectado


def estadisticos(x, parametros):
    """
    T² y Q de cada fila de x (n × 3) con el modelo PCA guardado.
    Filas con NaN devuelven NaN.
    """
    mu = np.array(parametros["mu"])
    s = np.array(parametros["s"])
    k = parametros["k"]
    P = np.array(parametros["P"])[:, :k]              # 3 × k, componentes retenidas
    lam = np.array(parametros["autovalores"])[:k]     # varianza de cada componente

    z = (x - mu) / s                 # estandarizar con μ y s de entrenamiento
    t = z @ P                        # puntajes: proyección de z sobre cada componente
    t2 = np.sum(t ** 2 / lam, axis=1)          # T² = Σ tᵢ²/λᵢ
    z_reconstruida = t @ P.T                   # P·Pᵀ·z : lo que explica el modelo
    q = np.sum((z - z_reconstruida) ** 2, axis=1)   # Q = ||z − P·Pᵀ·z||²
    return t2, q


def muestras_anomalas(t2, q, desconectado, parametros):
    """Muestra anómala: supera algún umbral o tiene un canal desconectado."""
    # Las comparaciones con NaN dan False: sin estadístico no hay anomalía por PCA.
    with np.errstate(invalid="ignore"):
        fuera = (t2 > parametros["umbral_T2"]) | (q > parametros["umbral_Q"])
    return fuera | desconectado


def aplicar_persistencia(anomala, K):
    """
    alarma[n] = True si las muestras n, n−1, …, n−K+1 son todas anómalas.
    Se lleva un contador de anomalías seguidas que vuelve a 0 con una muestra normal.
    """
    alarma = np.zeros(len(anomala), dtype=bool)
    seguidas = 0
    for n, a in enumerate(anomala):
        seguidas = seguidas + 1 if a else 0
        alarma[n] = seguidas >= K
    return alarma


# ==========================================
# ENTRENAMIENTO
# ==========================================


def main():
    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    coeficientes = cal.cargar_coeficientes()
    entrenamiento = pd.read_csv(CARPETA_DATOS / "entrenamiento.csv")

    # ---- 1. °C suavizados ----
    x, desconectado = preparar_datos(entrenamiento, coeficientes)
    validas = ~np.isnan(x).any(axis=1)
    X = x[validas]                       # n × 3, solo filas completas
    n = X.shape[0]
    print(f"Entrenamiento: {len(x)} muestras, {n} usadas "
          f"(las primeras {VENTANA_S - 1} no completan la ventana)")
    if desconectado.any():
        print("  ATENCIÓN: hay lecturas de desconexión en entrenamiento")

    # ---- 2a. Media de cada sensor ----
    mu = X.mean(axis=0)                                  # μ (vector de 3)
    # ---- 2b. Estandarizar ----
    s = X.std(axis=0, ddof=1)                            # desviación de cada sensor
    Z = (X - mu) / s                                     # cada columna: media 0, desv. 1
    # ---- 2c. Matriz de covarianza de Z (= matriz de correlación de X) ----
    R = Z.T @ Z / (n - 1)                                # 3 × 3
    # ---- 2d. Autovalores y autovectores ----
    # eigh es para matrices simétricas (R lo es) y los da de menor a mayor.
    autovalores, autovectores = np.linalg.eigh(R)
    orden = np.argsort(autovalores)[::-1]                # de mayor a menor
    autovalores = autovalores[orden]
    autovectores = autovectores[:, orden]                # cada COLUMNA es una componente
    # El signo de un autovector es arbitrario; se elige que su mayor elemento sea
    # positivo para que el resultado no cambie de una corrida a otra.
    for j in range(autovectores.shape[1]):
        if autovectores[np.argmax(np.abs(autovectores[:, j])), j] < 0:
            autovectores[:, j] *= -1

    # ---- 3. Número de componentes k ----
    fraccion = autovalores / autovalores.sum()           # varianza de cada componente
    acumulada = np.cumsum(fraccion)
    k = int(np.argmax(acumulada >= VARIANZA_OBJETIVO) + 1)

    tabla_autovalores = pd.DataFrame({
        "componente": np.arange(1, 4),
        "autovalor λ": autovalores,
        "varianza [%]": 100 * fraccion,
        "acumulada [%]": 100 * acumulada,
        "vector (sensor 1, 2, 3)": [np.round(autovectores[:, j], 3).tolist() for j in range(3)],
    })
    print("\n========== R12: AUTOVALORES DE R ==========")
    print(tabla_autovalores.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"Criterio fijado a priori: varianza acumulada ≥ {100 * VARIANZA_OBJETIVO:.0f} %  ->  k = {k}")

    grafica_codo(autovalores, acumulada, k)

    # ---- 4. T² y Q en entrenamiento ----
    parametros = {
        "descripcion": "Detector PCA de E3 (R12). Todo fijado SOLO con entrenamiento.csv. Datos SIMULADOS.",
        "Origen": "SIMULADO",
        "ventana_suavizado_s": VENTANA_S,
        "criterio_k": f"varianza acumulada >= {VARIANZA_OBJETIVO}",
        "percentil_umbral": PERCENTIL_UMBRAL,
        "K_persistencia": K_PERSISTENCIA,
        "mu": mu.tolist(),
        "s": s.tolist(),
        "P": autovectores.tolist(),           # 3 × 3; se usan las primeras k columnas
        "autovalores": autovalores.tolist(),
        "k": k,
    }
    t2, q = estadisticos(X, parametros)

    # ---- 5. Umbrales ----
    parametros["umbral_T2"] = float(np.percentile(t2, PERCENTIL_UMBRAL))
    parametros["umbral_Q"] = float(np.percentile(q, PERCENTIL_UMBRAL))
    print(f"\nUmbral T² (percentil {PERCENTIL_UMBRAL}): {parametros['umbral_T2']:.4f}")
    print(f"Umbral Q  (percentil {PERCENTIL_UMBRAL}): {parametros['umbral_Q']:.4f}")
    print(f"Alarma: algún umbral superado (o canal desconectado) {K_PERSISTENCIA} muestras seguidas")

    # ---- R14: compresión y reconstrucción ----
    info = float(autovalores[:k].sum() / autovalores.sum())
    compresion = 3 / k
    error_rec = float(np.mean(q))
    parametros["R14"] = {
        "informacion_conservada": info,
        "factor_compresion": compresion,
        "error_reconstruccion_Q_medio": error_rec,
    }
    print("\n========== R14: COMPRESIÓN ==========")
    print(f"(i)   Información conservada = Σλ(1..k)/Σλ = {info:.4f} ({100 * info:.1f} %)")
    print(f"      -> con {k} de 3 componentes se conserva el {100 * info:.1f} % de la variación de los datos.")
    print(f"(ii)  Factor de compresión = 3/k = {compresion:.2f}")
    print(f"      -> cada muestra se guarda con {k} número(s) en vez de 3.")
    print(f"(iii) Error de reconstrucción = promedio de Q = {error_rec:.4f} (unidades de z²)")
    print(f"      -> de una varianza total de 3, se pierde {error_rec:.4f} "
          f"(≈ {100 * error_rec / 3:.1f} %, coherente con 1 − información conservada).")

    RUTA_PARAMETROS.write_text(json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8")
    tabla_autovalores.to_csv(CARPETA_RESULTADOS / "tabla_autovalores.csv", index=False)
    print(f"\nGuardado: {RUTA_PARAMETROS.relative_to(RAIZ_REPO)}")
    print("Guardado: E3_eventos/resultados/tabla_autovalores.csv, codo_pca.png")


def grafica_codo(autovalores, acumulada, k):
    fig, eje = plt.subplots(figsize=(6, 4))
    componentes = np.arange(1, len(autovalores) + 1)
    eje.plot(componentes, autovalores, "o-", label="autovalor λ")
    eje.set_xlabel("componente")
    eje.set_ylabel("autovalor λ")
    eje.set_xticks(componentes)
    eje2 = eje.twinx()
    eje2.plot(componentes, 100 * acumulada, "s--", color="tab:green", label="varianza acumulada")
    eje2.axhline(100 * VARIANZA_OBJETIVO, color="gray", ls=":", label=f"criterio {100 * VARIANZA_OBJETIVO:.0f} %")
    eje2.set_ylabel("varianza acumulada [%]")
    eje2.set_ylim(0, 105)
    eje.axvline(k, color="tab:red", alpha=0.3, lw=8, label=f"k = {k}")
    lineas = eje.get_legend_handles_labels()[0] + eje2.get_legend_handles_labels()[0]
    etiquetas = eje.get_legend_handles_labels()[1] + eje2.get_legend_handles_labels()[1]
    eje.legend(lineas, etiquetas, loc="center right", fontsize=8)
    eje.set_title("Gráfica de codo del PCA (entrenamiento) — SIMULADO")
    fig.tight_layout()
    fig.savefig(CARPETA_RESULTADOS / "codo_pca.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
