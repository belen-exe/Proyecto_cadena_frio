# Resultados E1 — Calibración (R4–R7)

> Generado por `E1_calibracion/calibracion.py`. Datos **SIMULADOS**.

## R4 — Datos

- 28 puntos de calibración y 10 de prueba
  (9 y 4 en 0–10 °C),
  rango 0.5–45.1 °C.
- Cada punto es el promedio de 10 lecturas ADC
  (desviación estándar típica dentro del escalón: 2.16 cuentas).
- Referencia: Termómetro digital de referencia con sonda (SIMULADO); resolución 0.1 °C,
  incertidumbre = exactitud de la ficha técnica = ±0.1 °C. Fuente: Ficha técnica supuesta de un termómetro digital de laboratorio: exactitud ±0,1 °C en 0–50 °C, resolución 0,1 °C. Valores SUPUESTOS para la simulación.

## R5 — Estructuras y selección

- **M1_lineal_adc**: T = θ0 + θ1·u,  u = x/4095 (2 parámetros)
- **M2_beta**: 1/T_K = θ0 + θ1·L,  L = ln(x/(4095−x)) (2 parámetros)
- **M3_steinhart_hart**: 1/T_K = θ0 + θ1·L + θ2·L² + θ3·L³ (4 parámetros)

Criterio de generalización: RMSE de **validación cruzada**, calculado solo con los
puntos de calibración y promediado en los 3 canales. Con los 28 puntos se hacen 28
rondas: en cada una se ajusta con 27 puntos y se predice el que quedó fuera.

| estructura | num_parametros | RMSE_entrenamiento_C | RMSE_validacion_cruzada_C |
|---|---|---|---|
| M1_lineal_adc | 2 | 0.4321 | 0.4763 |
| M2_beta | 2 | 0.0606 | 0.06542 |
| M3_steinhart_hart | 4 | 0.05842 | 0.06851 |

- El RMSE de **entrenamiento** baja siempre al agregar parámetros (menos sesgo).
- El RMSE de **validación cruzada** deja de mejorar (o empeora) cuando el modelo
  empieza a ajustar ruido: ahí domina la varianza.
- Regla: la estructura más simple con RMSE de validación cruzada ≤ 1.05 × mínimo.
  **Seleccionada: M2_beta** (1/T_K = θ0 + θ1·L,  L = ln(x/(4095−x))).

Detalle por canal: `tabla_modelos.csv`. Gráfica: `sesgo_varianza.png`.

## R6 — Ajuste por canal (ecuaciones normales, implementación propia)

Criterio: mínimos cuadrados en la variable y = 1/T_K, resuelto con las
ecuaciones normales: **θ = (XᵀX)⁻¹·Xᵀ·y** (matriz de diseño X por canal).
Coeficientes con su incertidumbre (error estándar = raíz de la diagonal de cov = s²·(XᵀX)⁻¹):

| canal | parametro | valor | error_estandar | error_relativo_% |
|---|---|---|---|---|
| 1 | θ0 | 0.00335566 | 1.55042e-07 | 0.00462031 |
| 1 | θ1 | 0.000252583 | 2.26655e-07 | 0.089735 |
| 2 | θ0 | 0.00335637 | 1.49785e-07 | 0.00446271 |
| 2 | θ1 | 0.000254023 | 2.20523e-07 | 0.0868121 |
| 3 | θ0 | 0.00335298 | 1.46861e-07 | 0.00438002 |
| 3 | θ1 | 0.00025487 | 2.1549e-07 | 0.084549 |

Condiciones de optimalidad (∇J = −2Xᵀr ≈ 0; ∇²J = 2XᵀX con autovalores > 0 → mínimo
global único) y confiabilidad numérica (número de condición y diferencia relativa
entre las ecuaciones normales y la SVD):

| canal | gradiente máx. (∇J) | gradiente relativo | λ mín. hessiano | λ máx. hessiano | cond(X) | cond(XᵀX) | dif. normales vs SVD |
|---|---|---|---|---|---|---|---|
| 1 | 6.07e-17 | 1.4e-12 | 21.4 | 60.8 | 1.69 | 2.85 | 2.58e-16 |
| 2 | 7.89e-17 | 1.88e-12 | 21.2 | 60.6 | 1.69 | 2.86 | 2.56e-15 |
| 3 | 2.78e-17 | 6.77e-13 | 20.9 | 61.1 | 1.71 | 2.93 | 1.06e-15 |

**Intervalo de predicción al 95 %** de una nueva lectura:
ŷ ± t·s·√(1 + x₀ᵀ(XᵀX)⁻¹x₀) (t de la tabla t), transformado a °C. Evaluado en los
puntos de prueba; si está bien calculado, cerca del 95 % de ellos deben caer dentro.
Banda completa en `residuos_calibracion.png`.

| canal | semiancho medio [°C] | puntos dentro | cobertura [%] |
|---|---|---|---|
| 1 | 0.142 | 9 de 10 | 90 |
| 2 | 0.137 | 9 de 10 | 90 |
| 3 | 0.133 | 10 de 10 | 100 |

## R7 — Exactitud en los puntos de prueba

Error de cada punto = T_ref − T_estimada.

**Todo el rango (0–45 °C)**, meta RMSE ≤ 0.6 °C:

| canal | n puntos | RMSE [°C] | sesgo [°C] | desv. est. [°C] | error máx. [°C] | meta [°C] | cumple |
|---|---|---|---|---|---|---|---|
| 1 | 10 | 0.057 | 0.028 | 0.050 | 0.128 | 0.600 | sí |
| 2 | 10 | 0.065 | 0.036 | 0.054 | 0.128 | 0.600 | sí |
| 3 | 10 | 0.062 | 0.036 | 0.051 | 0.107 | 0.600 | sí |

**Zona crítica (0–10 °C)**, meta RMSE ≤ 0.4 °C:

| canal | n puntos | RMSE [°C] | sesgo [°C] | desv. est. [°C] | error máx. [°C] | meta [°C] | cumple |
|---|---|---|---|---|---|---|---|
| 1 | 4 | 0.083 | 0.078 | 0.030 | 0.128 | 0.400 | sí |
| 2 | 4 | 0.099 | 0.096 | 0.023 | 0.128 | 0.400 | sí |
| 3 | 4 | 0.090 | 0.088 | 0.018 | 0.107 | 0.400 | sí |

**Se cumplen las dos metas en los 3 canales.**

Análisis del error: RMSE² = sesgo² + desv. est.². El error de prueba incluye el error
del propio termómetro de referencia (±0.1 °C), que es un piso: ningún modelo
puede tener un RMSE de prueba mucho menor que ese valor. La resolución del ADC
(≈ 0,024 °C/cuenta, ver R1) y el ruido promediado en 10 muestras
aportan mucho menos.
