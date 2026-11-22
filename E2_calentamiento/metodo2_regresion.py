"""
Método 2 (R9): identificación de k por regresión lineal de la ecuación discreta.

Solución exacta del modelo de Newton en un paso Δt con ambiente constante:

    T[n+1] = T_amb[n] + (T[n] − T_amb[n])·exp(−k·Δt)

Restando T[n] a ambos lados:

    ΔT[n] = T[n+1] − T[n] = b · (T_amb[n] − T[n]),     b = 1 − exp(−k·Δt)

Es una regresión lineal por el origen en un solo parámetro b, que se resuelve con
el mínimos cuadrados PROPIO de comun/estadistica.py. Luego:

    k = −ln(1 − b) / Δt,     σ_k ≈ σ_b / ((1 − b)·Δt)   (propagación lineal)

Se trabaja con promedios de 1 min: así el ruido de T[n] (que también aparece en
el regresor) queda muy por debajo de la variación de (T_amb − T), y el sesgo por
error en las variables es despreciable.

Este método es INDEPENDIENTE del PSO: no simula la trayectoria completa ni usa T0,
solo relaciona cada paso con el siguiente (error de ecuación).
"""

import numpy as np

from comun.estadistica import ajustar_mco, t_cuantil


def autocorrelacion_lag1(residuos):
    r = np.asarray(residuos) - np.mean(residuos)
    return float(np.sum(r[1:] * r[:-1]) / np.sum(r * r))


def estimar_k_regresion(t_min, temperatura, t_amb, confianza=0.95):
    """
    t_min, temperatura, t_amb: series uniformes (promedios de 1 min).
    Devuelve k [1/min], su IC y los diagnósticos del ajuste.
    """
    t_min = np.asarray(t_min, dtype=float)
    temperatura = np.asarray(temperatura, dtype=float)
    t_amb = np.asarray(t_amb, dtype=float)
    dt = float(np.median(np.diff(t_min)))

    delta = temperatura[1:] - temperatura[:-1]
    # Ambiente promedio en el intervalo [n, n+1]
    regresor = 0.5 * (t_amb[1:] + t_amb[:-1]) - temperatura[:-1]

    ajuste = ajustar_mco(regresor[:, None], delta)
    b = float(ajuste["theta"][0])
    se_b = float(ajuste["error_estandar"][0])

    # Corrección por autocorrelación de los residuos (tamaño de muestra efectivo)
    rho = autocorrelacion_lag1(ajuste["residuos"])
    rho_usado = max(rho, 0.0)
    inflacion = np.sqrt((1 + rho_usado) / (1 - rho_usado))
    n_efectivo = ajuste["n"] * (1 - rho_usado) / (1 + rho_usado)
    gl = max(n_efectivo - 1, 1)

    k = -np.log(1 - b) / dt
    se_k = se_b * inflacion / ((1 - b) * dt)
    t = t_cuantil(0.5 + confianza / 2, gl)

    return {
        "k_1_por_min": k,
        "se_k": se_k,
        "IC95": (k - t * se_k, k + t * se_k),
        "b": b,
        "se_b": se_b,
        "dt_min": dt,
        "n": ajuste["n"],
        "rho_lag1": rho,
        "n_efectivo": n_efectivo,
        "s_residual_C": ajuste["s"],
        "residuos": ajuste["residuos"],
        "diagnostico": ajuste["diagnostico"],
    }
