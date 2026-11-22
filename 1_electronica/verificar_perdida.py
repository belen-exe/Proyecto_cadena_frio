"""
R2 - Verificación de la pérdida de muestras en una captura del firmware.

Definición (Sección 8 del enunciado):
    pérdida [%] = (muestras esperadas − muestras válidas en el CSV) / esperadas · 100
    muestras esperadas = round( (t_último − t_primero) / Ts ) + 1

Criterio de aceptación de R2: pérdida ≤ 0,5 % en un registro de al menos 10 min.

La captura es el texto copiado del monitor serie de Wokwi. Se ignoran las líneas
anteriores al encabezado (mensajes de arranque del ESP32) y las que empiezan
por '#'. Una línea incompleta o ilegible cuenta como muestra perdida.

Uso:
    python 1_electronica/verificar_perdida.py [ruta_captura.csv]
    (por defecto: 1_electronica/pruebas_simulacion/captura_10min.csv)

Crea: 1_electronica/resultados/perdida_muestras.md
"""

import sys
from pathlib import Path

import numpy as np

CARPETA = Path(__file__).resolve().parent
CAPTURA_POR_DEFECTO = CARPETA / "pruebas_simulacion" / "captura_10min.csv"
CARPETA_RESULTADOS = CARPETA / "resultados"

TS_MS = 1000                 # Debe coincidir con TS_MS del firmware
DURACION_MIN_S = 10 * 60     # R2: al menos 10 minutos
PERDIDA_MAX_PCT = 0.5        # R2

ENCABEZADO = "t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,alarma,Origen"
NUM_CAMPOS = len(ENCABEZADO.split(","))


def leer_captura(ruta):
    """Devuelve (tiempos_ms válidos, número de líneas inválidas, filas válidas)."""
    lineas = Path(ruta).read_text(encoding="utf-8", errors="replace").splitlines()

    try:
        inicio = next(i for i, l in enumerate(lineas) if l.strip() == ENCABEZADO)
    except StopIteration:
        sys.exit(f"No se encontró el encabezado '{ENCABEZADO}' en {ruta}")

    tiempos, filas, invalidas = [], [], 0
    for linea in lineas[inicio + 1:]:
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        campos = linea.split(",")
        try:
            if len(campos) != NUM_CAMPOS or campos[-1] != "SIMULADO":
                raise ValueError
            t = int(campos[0])
            [int(c) for c in campos[1:4]]
        except ValueError:
            invalidas += 1
            continue
        tiempos.append(t)
        filas.append(campos)

    return np.array(tiempos), invalidas, filas


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else CAPTURA_POR_DEFECTO
    if not ruta.exists():
        sys.exit(f"No existe la captura {ruta}. Grábela siguiendo 1_electronica/README.md.")

    tiempos, invalidas, filas = leer_captura(ruta)
    tiempos = np.unique(tiempos)  # una muestra repetida no cuenta dos veces

    duracion_s = (tiempos[-1] - tiempos[0]) / 1000
    esperadas = int(round((tiempos[-1] - tiempos[0]) / TS_MS)) + 1
    validas = len(tiempos)
    perdida_pct = max(0.0, 100 * (esperadas - validas) / esperadas)

    periodos = np.diff(tiempos)
    huecos = int(np.sum(periodos > 1.5 * TS_MS))
    alarmas = sum(f[7] == "1" for f in filas)
    na = sum("NA" in f[4:7] for f in filas)

    cumple_duracion = duracion_s >= DURACION_MIN_S
    cumple_perdida = perdida_pct <= PERDIDA_MAX_PCT

    informe = f"""# Pérdida de muestras (R2)

> Generado por `1_electronica/verificar_perdida.py` a partir de `{ruta.name}` (SIMULADO, Wokwi).

| Magnitud | Valor |
|---|---|
| Duración registrada | {duracion_s:.1f} s ({duracion_s / 60:.2f} min) — {"cumple" if cumple_duracion else "NO cumple"} ≥ 10 min |
| Ts nominal | {TS_MS} ms |
| Muestras esperadas | {esperadas} |
| Muestras válidas | {validas} |
| Líneas inválidas descartadas | {invalidas} |
| **Pérdida de muestras** | **{perdida_pct:.3f} %** — {"cumple" if cumple_perdida else "NO cumple"} ≤ {PERDIDA_MAX_PCT} % |
| Periodo medio / desviación | {periodos.mean():.2f} ms / {periodos.std():.2f} ms |
| Periodo mínimo / máximo | {periodos.min()} ms / {periodos.max()} ms |
| Huecos (> 1,5·Ts) | {huecos} |
| Filas con alarma / con NA | {alarmas} / {na} |
"""
    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    salida = CARPETA_RESULTADOS / "perdida_muestras.md"
    salida.write_text(informe, encoding="utf-8")

    print(f"Duracion: {duracion_s / 60:.2f} min | esperadas: {esperadas} | validas: {validas} | "
          f"perdida: {perdida_pct:.3f} %")
    print(f"Periodo: media {periodos.mean():.2f} ms, max {periodos.max()} ms, huecos {huecos}")
    print("R2:", "CUMPLE" if (cumple_duracion and cumple_perdida) else "NO CUMPLE")
    print(f"Generado: {salida}")


if __name__ == "__main__":
    main()
