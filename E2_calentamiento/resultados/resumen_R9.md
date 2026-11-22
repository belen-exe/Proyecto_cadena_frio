# Resultados R9 — Modelo dinámico e identificación

> Generado por `E2_calentamiento/identificacion.py`. Datos **SIMULADOS**.

## Modelo

dT/dt = k·(T_amb(t) − T),  T(t_ext) = T0.  Solución exacta por paso (Δt):
T[n+1] = T_amb[n] + (T[n] − T_amb[n])·e^(−k·Δt).  τ = 1/k.

Datos: 60 min posteriores a la extracción; T interior = promedio de los 3 canales
calibrados (E1); T_amb medida cada 60 s e interpolada. T_amb media = 22.63 °C.

## Resultados

| Método | k [1/min] | u estadística | u sistemática | **IC 95 % de k [1/min]** | τ [min] | Otros |
|---|---|---|---|---|---|---|
| 1. PSO propio (k, T0) | 0.004516 | 3.38e-06 | 2.60e-05 | **[0.004464, 0.004569]** | 221.4 | T0 = 4.976 °C, s = 0.0171 °C |
| 2. Regresión de la ecuación discreta | 0.004531 | 8.04e-05 | 2.59e-05 | **[0.004362, 0.004700]** | 220.7 | b = 0.004520, Δt = 1 min |

- Diferencia relativa: **+0.32 %** (0.18 errores estándar combinados);
  los intervalos se solapan: ambos métodos son comparables.
- El PSO se corrió con 5 semillas: dispersión relativa de k =
  1.8e-05 % (converge siempre al mismo mínimo,
  ver `convergencia_pso.png`).

## Cálculo del intervalo al 95 % de k

- **PSO:** linealización alrededor del óptimo. J = ∂T_modelo/∂θ por diferencias centrales;
  cov(θ) = s²·(JᵀJ)⁻¹ con s² = SSE/(n − 2). Como los residuos de puntos vecinos están
  correlacionados (ρ1 = -0.04), la covarianza se multiplica por (1+ρ1)/(1−ρ1) y se usa
  n_efectivo = n·(1−ρ1)/(1+ρ1) = 360 para los grados de libertad.
  IC = k ± t(0,975; n_ef − 2)·σ_k.
- **Parte sistemática (ambos métodos):** se repite la identificación con T_amb + u_ref
  (u_ref = 0.0645 °C, termómetro de referencia, E1) y con T + u_cal (u_cal = 0.0615 °C,
  RMSE de prueba de la calibración, E1); u_sis = √(Δk_ref² + Δk_cal²).
- **Combinación:** u_k = √(u_estadística² + u_sis²); IC 95 % = k ± 2·u_k (factor de cobertura 2).
  Con solo la parte estadística el IC del PSO sería [0.004510, 0.004523],
  demasiado optimista: el error de los instrumentos domina.
- **Regresión:** σ_b de mínimos cuadrados (con la misma corrección por autocorrelación,
  ρ1 = -0.36) y propagación a k = −ln(1−b)/Δt: σ_k = σ_b/((1−b)·Δt).

## Por qué pueden diferir

El PSO ajusta la trayectoria completa (error de salida) y estima también T0; la
regresión solo relaciona cada minuto con el siguiente (error de ecuación) y es más
sensible al ruido de los incrementos, por eso su intervalo es más ancho.

Gráficas: `datos_E2.png`, `datos_vs_modelo.png`, `residuos.png`, `convergencia_pso.png`.
