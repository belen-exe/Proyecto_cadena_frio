# Resultados E1 — Calibración (R4–R7)

> Generado por `E1_calibracion/calibracion.py`. Datos **SIMULADOS**.

## R4 — Datos

- 28 puntos de calibración y 10 de prueba
  (9 y 4 en 0–10 °C),
  rango 0.5–45.1 °C.
- Cada punto es el promedio de 10 lecturas ADC
  (desviación estándar típica dentro del escalón: 2.16 cuentas).
- Referencia: Termómetro digital de referencia con sonda (SIMULADO); resolución 0.1 °C,
  exactitud ±0.1 °C → u = 0.0645 °C (tipo B, distribuciones
  rectangulares). Fuente: Ficha técnica supuesta de un termómetro digital de laboratorio: exactitud ±0,1 °C en 0–50 °C, resolución 0,1 °C. Valores SUPUESTOS para la simulación.

## R5 — Estructuras y selección

- **M1_lineal_adc**: T = θ0 + θ1·u,  u = x/4095 (2 parámetros)
- **M2_beta**: 1/T_K = θ0 + θ1·L,  L = ln(x/(4095−x)) (2 parámetros)
- **M3_steinhart_hart**: 1/T_K = θ0 + θ1·L + θ2·L² + θ3·L³ (4 parámetros)

Criterio de generalización: RMSE de validación cruzada dejando uno fuera (LOO),
calculado solo con los puntos de calibración y promediado en los 3 canales.

| estructura | num_parametros | RMSE_entrenamiento_C | RMSE_LOO_C |
|---|---|---|---|
| M1_lineal_adc | 2 | 0.4321 | 0.4763 |
| M2_beta | 2 | 0.0606 | 0.06542 |
| M3_steinhart_hart | 4 | 0.05842 | 0.06851 |

- El RMSE de **entrenamiento** baja siempre al agregar parámetros (menos sesgo).
- El RMSE **LOO** deja de mejorar (o empeora) cuando el modelo empieza a ajustar
  ruido: ahí domina la varianza.
- Regla: la estructura más simple con RMSE_LOO ≤ 1.05 × mínimo.
  **Seleccionada: M2_beta** (1/T_K = θ0 + θ1·L,  L = ln(x/(4095−x))).

Detalle por canal: `tabla_modelos.csv`. Gráfica: `sesgo_varianza.png`.

## R6 — Ajuste por canal (QR propio)

Criterio: mínimos cuadrados en la variable y = 1/T_K.
Coeficientes ± error estándar (cov = s²·(XᵀX)⁻¹) e IC 95 % con t de Student:

| canal | parametro | valor | error_estandar | IC95_inf | IC95_sup | error_relativo_% |
|---|---|---|---|---|---|---|
| 1 | θ0 | 0.00335566 | 1.55042e-07 | 0.00335534 | 0.00335598 | 0.00462031 |
| 1 | θ1 | 0.000252583 | 2.26655e-07 | 0.000252117 | 0.000253049 | 0.089735 |
| 2 | θ0 | 0.00335637 | 1.49785e-07 | 0.00335606 | 0.00335668 | 0.00446271 |
| 2 | θ1 | 0.000254023 | 2.20523e-07 | 0.00025357 | 0.000254476 | 0.0868121 |
| 3 | θ0 | 0.00335298 | 1.46861e-07 | 0.00335268 | 0.00335328 | 0.00438002 |
| 3 | θ1 | 0.00025487 | 2.1549e-07 | 0.000254427 | 0.000255313 | 0.084549 |

Condiciones de optimalidad (∇J = −2Xᵀr ≈ 0; ∇²J = 2XᵀX con autovalores > 0 → mínimo
global único) y confiabilidad numérica (número de condición y diferencia relativa
entre QR, ecuaciones normales, SVD y `numpy.linalg.lstsq`, esta última **solo como
contraste con una función de librería**):

| canal | max|∇J| | |Xᵀr| relativo | λmin(∇²J) | λmax(∇²J) | cond(X) | cond(XᵀX) | dif QR-normales | dif QR-SVD | dif QR-lstsq (contraste) |
|---|---|---|---|---|---|---|---|---|---|
| 1.000e+00 | 9.541e-18 | 2.197e-13 | 2.137e+01 | 6.083e+01 | 1.687e+00 | 2.846e+00 | 4.292e-16 | 8.585e-16 | 6.439e-16 |
| 2.000e+00 | 8.856e-18 | 2.111e-13 | 2.120e+01 | 6.064e+01 | 1.691e+00 | 2.860e+00 | 4.268e-16 | 2.347e-15 | 8.536e-16 |
| 3.000e+00 | 5.206e-18 | 1.269e-13 | 2.089e+01 | 6.112e+01 | 1.710e+00 | 2.925e+00 | 1.063e-15 | 2.127e-16 | 1.489e-15 |

Intervalo de predicción al 95 % de una nueva lectura:
ŷ ± t(0,975; gl)·s·√(1 + x₀ᵀ(XᵀX)⁻¹x₀), transformado a °C. Semiancho medio y cobertura
en los puntos de prueba en la tabla de R7; banda completa en `residuos_calibracion.png`.

## R7 — Exactitud en los puntos de prueba

| canal | RMSE_0_45C | RMSE_0_10C | n_prueba | n_prueba_0_10C | sesgo_medio_C | desv_est_C | error_max_abs_C | semiancho_IP95_medio_C | cobertura_IP95_% | cumple_0_45 | cumple_0_10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05705 | 0.0833 | 10 | 4 | 0.02756 | 0.04995 | 0.1281 | 0.1416 | 90 | True | True |
| 2 | 0.06512 | 0.099 | 10 | 4 | 0.03624 | 0.0541 | 0.128 | 0.137 | 90 | True | True |
| 3 | 0.06245 | 0.09008 | 10 | 4 | 0.03564 | 0.05128 | 0.1071 | 0.1334 | 100 | True | True |

Metas: RMSE ≤ 0.6 °C en 0–45 °C y ≤ 0.4 °C en 0–10 °C.
**Se cumplen en los 3 canales.**

Análisis del error: RMSE² = sesgo² + varianza. El error de prueba incluye el error
del propio termómetro de referencia (u = 0.0645 °C), que es un piso: ningún modelo
puede tener un RMSE de prueba mucho menor que ese valor. La resolución del ADC
(≈ 0,024 °C/cuenta, ver R1) y el ruido promediado en 10 muestras
aportan mucho menos.
