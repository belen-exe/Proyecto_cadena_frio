# E1_calibracion — Experimento E1 y calibración ADC → temperatura (R4–R7)

**Estado: Hecho** (datos SIMULADOS).

## Cómo ejecutarlo (desde la raíz del repositorio)

```bash
python E1_calibracion/simulador_E1.py          # 1. genera los datos crudos
python E1_calibracion/calibracion.py           # 2. R5, R6, R7 -> resultados/
python E1_calibracion/comparar_con_verdad.py   # 3. (opcional) verificación final
```

## Archivos

| Archivo | Qué es |
|---|---|
| `simulador_E1.py` | Simula el baño de calibración: 3 sensores + termómetro de referencia en el mismo recipiente, de 0 a 45 °C |
| `calibracion.py` | Compara 3 estructuras de modelo (R5), ajusta con ecuaciones normales θ = (XᵀX)⁻¹·Xᵀ·y (R6) y evalúa el RMSE en los puntos de prueba (R7) |
| `comparar_con_verdad.py` | Único script que lee `VERDAD_NO_USAR.json`; solo verifica al final |
| `datos/calibracion_E1.csv` | Datos crudos: una fila por muestra |
| `datos/instrumento_referencia.json` | Incertidumbre del termómetro de referencia y su fuente (R4-iii) |
| `datos/VERDAD_NO_USAR.json` | Temperaturas reales del baño. **El análisis no lo lee** |
| `resultados/coeficientes_calibracion.json` | **Salida principal:** estructura elegida, coeficientes, covarianza, s y gl por canal. La leen E2 (y luego E3 y el firmware) |
| `resultados/resumen_E1.md` | Resumen con todas las tablas de R4–R7 |
| `resultados/tabla_*.csv` | Comparación de modelos, coeficientes con su error estándar, diagnóstico numérico y RMSE |
| `resultados/*.png` | Sesgo vs varianza, residuos con intervalo de predicción y curvas de calibración |

## Diseño del experimento

- 28 puntos de calibración y 10 de prueba (9 y 4 de ellos en 0–10 °C). El tipo de
  cada punto se fija **antes** de medir (columna `tipo`), así que los de prueba nunca
  entran en el ajuste ni en la selección del modelo.
- Cada punto promedia 10 lecturas ADC tomadas a Ts = 1 s.
- Referencia: resolución 0,1 °C y exactitud ±0,1 °C (ficha técnica supuesta),
  con u = 0,065 °C.

## Qué revisar para saber que funciona

Al ejecutar `calibracion.py`:
- **R5:** el RMSE de entrenamiento baja al aumentar los parámetros, mientras que el
  RMSE de validación cruzada tiene un mínimo. El modelo elegido es el más
  simple cerca de ese mínimo.
- **R6:** `max|∇J|` ≈ 0, `λmin(∇²J)` > 0, cond(X) pequeño, y diferencias normales / QR /
  SVD del orden de 1e-15.
- **R7:** la línea final dice `R7: CUMPLE las metas en todos los canales`
  (RMSE ≤ 0,6 °C en 0–45 °C y ≤ 0,4 °C en 0–10 °C).

Al ejecutar `comparar_con_verdad.py`: la curva calibrada debe quedar a pocas
centésimas de °C de la curva real de cada sensor.
