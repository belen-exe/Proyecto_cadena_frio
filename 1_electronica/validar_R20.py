"""
R20 - Validación cruzada ESP32 – Python.

Toma una captura del monitor serie del ESP32 (firmware de R19) y, con las MISMAS
lecturas ADC que leyó el ESP32, recalcula en Python:
  - la temperatura calibrada de cada canal (comun/calibracion.py, coeficientes de E1);
  - T², Q y la alarma del detector (E3_eventos/detector.py, parámetros de E3).
Compara ambos resultados y reporta:
  - diferencia máxima de temperatura (meta R20: ≤ 0,05 °C);
  - diferencia máxima de T² y Q, y coincidencia de la alarma;
  - tiempo de procesamiento por ciclo (columna t_proc_us, medida con micros());
  - memoria (heap libre que informa el ESP32 al arrancar).

Genera en 1_electronica/resultados/:
  comparacion_R20.csv   tabla muestra a muestra (ESP32 vs Python)
  validacion_R20.md     resumen

Uso:  python 1_electronica/validar_R20.py [captura.csv]
      (por defecto 1_electronica/pruebas_simulacion/captura_R20.csv)
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from comun import calibracion as cal  # noqa: E402
from E3_eventos import detector as det  # noqa: E402

CARPETA = Path(__file__).resolve().parent
CAPTURA_POR_DEFECTO = CARPETA / "pruebas_simulacion" / "captura_R20.csv"
CARPETA_RESULTADOS = CARPETA / "resultados"

ENCABEZADO = "t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,T2,Q,alarma,t_proc_us,Origen"
MIN_MUESTRAS = 50          # R20
META_DIF_TEMP_C = 0.05     # R20


def leer_captura(ruta):
    """Devuelve (tabla con las filas de datos, heap libre informado o None)."""
    lineas = Path(ruta).read_text(encoding="utf-8", errors="replace").splitlines()
    heap = None
    for l in lineas:
        m = re.search(r"heap\).*?:\s*(\d+)", l)
        if m:
            heap = int(m.group(1))
    try:
        inicio = next(i for i, l in enumerate(lineas) if l.strip() == ENCABEZADO)
    except StopIteration:
        sys.exit(f"No se encontró el encabezado del firmware de R19 en {ruta}")

    columnas = ENCABEZADO.split(",")
    filas = []
    for l in lineas[inicio + 1:]:
        campos = l.strip().split(",")
        if l.startswith("#") or len(campos) != len(columnas) or campos[-1] != "SIMULADO":
            continue   # mensajes de alarma, líneas cortadas, etc.
        filas.append(campos)
    tabla = pd.DataFrame(filas, columns=columnas).replace("NA", np.nan)
    for c in columnas[:-1]:
        tabla[c] = pd.to_numeric(tabla[c])
    return tabla, heap


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else CAPTURA_POR_DEFECTO
    if not ruta.exists():
        sys.exit(f"No existe {ruta}. Grábela siguiendo 1_electronica/README.md (sección R20).")
    esp, heap = leer_captura(ruta)
    if len(esp) < MIN_MUESTRAS:
        sys.exit(f"La captura tiene {len(esp)} muestras; R20 pide al menos {MIN_MUESTRAS}.")
    if (np.diff(esp["t_ms"]) != 1000).any():
        print("ATENCIÓN: faltan filas en la captura; el promedio móvil de Python no coincidirá "
              "con el del ESP32 justo después de cada hueco.")

    # ---- Python con las mismas lecturas ADC ----
    coeficientes = cal.cargar_coeficientes()
    parametros = json.loads(det.RUTA_PARAMETROS.read_text(encoding="utf-8"))
    py = pd.DataFrame({"t_ms": esp["t_ms"]})
    for c in (1, 2, 3):
        py[f"T_{c}"] = cal.adc_a_temperatura_calibrada(esp[f"adc_{c}"].to_numpy(), c, coeficientes)
    x, desconectado = det.preparar_datos(esp, coeficientes, parametros["ventana_suavizado_s"])
    py["T2"], py["Q"] = det.estadisticos(x, parametros)
    anomala = det.muestras_anomalas(py["T2"].to_numpy(), py["Q"].to_numpy(), desconectado, parametros)
    py["alarma"] = det.aplicar_persistencia(anomala, parametros["K_persistencia"]).astype(int)

    # ---- Comparación ----
    tabla = pd.DataFrame({"t_ms": esp["t_ms"]})
    for c in (1, 2, 3):
        tabla[f"adc_{c}"] = esp[f"adc_{c}"]
    for col in ["T_1", "T_2", "T_3", "T2", "Q", "alarma"]:
        tabla[f"{col}_esp32"] = esp[col]
        tabla[f"{col}_python"] = py[col]
    tabla["t_proc_us"] = esp["t_proc_us"]

    dif_temp = np.nanmax(np.abs(esp[["T_1", "T_2", "T_3"]].to_numpy() - py[["T_1", "T_2", "T_3"]].to_numpy()))
    dif_t2 = np.nanmax(np.abs(esp["T2"] - py["T2"]))
    dif_q = np.nanmax(np.abs(esp["Q"] - py["Q"]))
    # NA en el mismo lugar en ambos (desconexiones y ventana incompleta)
    mismos_na = bool((esp[["T_1", "T_2", "T_3", "T2", "Q"]].isna().to_numpy()
                      == py[["T_1", "T_2", "T_3", "T2", "Q"]].isna().to_numpy()).all())
    coincide_alarma = float(np.mean(esp["alarma"].to_numpy() == py["alarma"].to_numpy()))
    cumple = dif_temp <= META_DIF_TEMP_C

    print(f"Muestras comparadas: {len(tabla)}")
    print(f"Diferencia máxima de temperatura: {dif_temp:.5f} °C (meta ≤ {META_DIF_TEMP_C}) -> "
          f"{'CUMPLE' if cumple else 'NO CUMPLE'}")
    print(f"Diferencia máxima T²: {dif_t2:.5f}   Q: {dif_q:.5f}")
    print(f"NA en los mismos lugares: {'sí' if mismos_na else 'NO'}   "
          f"Alarma igual en el {100 * coincide_alarma:.1f} % de las muestras")
    print(f"Tiempo por ciclo: media {esp['t_proc_us'].mean():.0f} us, máximo {esp['t_proc_us'].max():.0f} us")
    print(f"Heap libre al iniciar: {heap} bytes" if heap else "Heap libre: no aparece en la captura")

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    tabla.to_csv(CARPETA_RESULTADOS / "comparacion_R20.csv", index=False)
    texto = f"""# R20 — Validación cruzada ESP32 – Python (SIMULADO)

Captura: `{ruta.relative_to(RAIZ).as_posix() if ruta.is_relative_to(RAIZ) else ruta.name}`.
Python recalcula todo con las **mismas lecturas ADC** que registró el ESP32.
Tabla muestra a muestra: `comparacion_R20.csv` ({len(tabla)} muestras).

| Resultado | Valor |
|---|---|
| Muestras comparadas | {len(tabla)} (mínimo {MIN_MUESTRAS}) |
| **Diferencia máxima de temperatura** | **{dif_temp:.5f} °C** (meta ≤ {META_DIF_TEMP_C} °C) → **{'CUMPLE' if cumple else 'NO CUMPLE'}** |
| Diferencia máxima de T² | {dif_t2:.5f} |
| Diferencia máxima de Q | {dif_q:.5f} |
| NA en los mismos lugares | {'sí' if mismos_na else 'no'} |
| Alarma igual en ambos | {100 * coincide_alarma:.1f} % de las muestras |
| Tiempo de procesamiento por ciclo (lectura + cálculo, `micros()`) | media {esp['t_proc_us'].mean():.0f} µs, máximo {esp['t_proc_us'].max():.0f} µs (Ts = 1 000 000 µs) |
| Memoria libre al iniciar (`ESP.getFreeHeap()`) | {heap if heap else 'no registrada'} bytes |
| Memoria usada según la compilación (`pio run`) | ver `1_electronica/README.md` |

Las pequeñas diferencias vienen de que el ESP32 calcula en `float` (≈ 7 cifras) y
Python en `double` (≈ 16 cifras), y de que el ESP32 imprime 4 decimales.
El tiempo de `micros()` es el que reporta el simulador Wokwi, no una placa real.
"""
    (CARPETA_RESULTADOS / "validacion_R20.md").write_text(texto, encoding="utf-8")
    print("Generado: 1_electronica/resultados/comparacion_R20.csv, validacion_R20.md")


if __name__ == "__main__":
    main()
