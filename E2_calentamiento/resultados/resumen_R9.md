# Resultados R9 — Modelo dinámico e identificación

> Generado por `E2_calentamiento/identificacion.py`. Datos **SIMULADOS**.

## Modelo

dT/dt = k·(T_amb(t) − T),  T(t_ext) = T0.  Solución exacta por paso (Δt):
T[n+1] = T_amb[n] + (T[n] − T_amb[n])·e^(−k·Δt).  τ = 1/k.

Datos: 60 min posteriores a la extracción; T interior = promedio de los 3 canales
calibrados (E1); T_amb medida cada 60 s e interpolada. T_amb media = 22.63 °C.

## Resultados

| Método | k [1/min] | τ [min] | Otros |
|---|---|---|---|
| 1. PSO propio (k, T0) | 0.004516 | 221.4 | T0 = 4.976 °C, s = 0.0171 °C |
| 2. Regresión de la ecuación discreta | 0.004531 | 220.7 | b = 0.004520, Δt = 1 min |

**Intervalo al 95 % de la rapidez de calentamiento k: [0.004368, 0.004693] min⁻¹**
(τ entre 213 y 229 min).

- Diferencia relativa entre métodos: **+0.32 %**. El k del PSO
  está dentro del intervalo: ambos métodos son comparables.
- El PSO se corrió con 5 semillas: dispersión relativa de k =
  1.8e-05 % (converge siempre al mismo mínimo,
  ver `convergencia_pso.png`).

## Cálculo del intervalo al 95 % de k

1. La regresión ΔT = b·(T_amb − T) se resuelve con θ = (XᵀX)⁻¹·Xᵀ·y (igual que en E1);
   el error estándar de b sale de cov = s²·(XᵀX)⁻¹: σ_b = 8.01e-05.
2. **Autocorrelación:** si cada residuo se parece al anterior (ρ1 = -0.36), los
   datos traen menos información independiente. Se usa n_efectivo = n·(1−ρ1)/(1+ρ1)
   = 59 (de n = 59) y σ_b se multiplica por √((1+ρ1)/(1−ρ1)).
   Si ρ1 ≤ 0 no se corrige.
3. Paso de b a k = −ln(1−b)/Δt con la derivada: σ_k = σ_b/((1−b)·Δt) = 8.04e-05 min⁻¹.
4. IC 95 % = k ± t·σ_k, con t de la tabla t para n_efectivo − 1 grados de libertad.

Limitación: el intervalo solo considera el ruido de las mediciones; no incluye el
error fijo de los instrumentos (termómetro de referencia y calibración de E1).

## Por qué pueden diferir los métodos

El PSO ajusta la trayectoria completa y estima también T0; la regresión solo relaciona
cada minuto con el siguiente y es más sensible al ruido de los incrementos.

Gráficas: `datos_E2.png`, `datos_vs_modelo.png`, `residuos.png`, `convergencia_pso.png`.
