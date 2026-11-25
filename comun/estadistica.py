"""
Herramientas estadísticas PROPIAS, usadas por E1 (calibración) y E2 (identificación).

- ajustar_mco: mínimos cuadrados ordinarios con álgebra matricial propia
  (ecuaciones normales θ = (XᵀX)⁻¹·Xᵀ·y), usando solo primitivas de numpy.linalg
  (inv, eigvalsh, cond). No usa funciones que hagan la regresión completa
  (lstsq, pinv, polyfit).
- t_tabla: valor t de Student para un intervalo al 95 %, tomado de la tabla t.
"""

import math

import numpy as np

# ==========================================
# 1. TABLA t DE STUDENT (95 %, dos colas: t con 0,975 de probabilidad acumulada)
# ==========================================

TABLA_T_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
    9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074,
    23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045,
    30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980,
}
T_95_INFINITO = 1.960


def t_tabla(gl):
    """
    Valor t para un intervalo al 95 % con gl grados de libertad, leído de la tabla.
    Si gl no está en la tabla se usa la fila inmediatamente menor (más conservadora).
    """
    if gl < 1:
        raise ValueError("Se necesita al menos 1 grado de libertad")
    if gl > max(TABLA_T_95):
        return T_95_INFINITO
    fila = max(g for g in TABLA_T_95 if g <= gl)
    return TABLA_T_95[fila]


# ==========================================
# 2. MÍNIMOS CUADRADOS ORDINARIOS (implementación propia)
# ==========================================


def ajustar_mco(X, y):
    """
    Resuelve  min_θ ||y − Xθ||²  con las ECUACIONES NORMALES:

        ∇J = −2·Xᵀ(y − Xθ) = 0   =>   (XᵀX)·θ = Xᵀ·y   =>   θ = (XᵀX)⁻¹·Xᵀ·y

    Devuelve un diccionario con:
        theta, residuos, s2 (varianza residual), gl (n − p), cov (s²·(XᵀX)⁻¹),
        error_estandar, y diagnósticos de optimalidad y de confiabilidad numérica.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    if n <= p:
        raise ValueError("Se necesitan más observaciones que parámetros")

    # --- Solución principal: ecuaciones normales  θ = (XᵀX)⁻¹·Xᵀ·y ---
    XtX = X.T @ X                  # matriz p × p
    Xty = X.T @ y                  # vector de p elementos
    XtX_inv = np.linalg.inv(XtX)   # (XᵀX)⁻¹
    theta = XtX_inv @ Xty          # θ = (XᵀX)⁻¹·Xᵀ·y

    residuos = y - X @ theta       # r = y − X·θ
    sse = float(residuos @ residuos)
    gl = n - p
    s2 = sse / gl                  # varianza del error
    cov = s2 * XtX_inv             # cov(θ) = s²·(XᵀX)⁻¹

    # --- Condiciones de optimalidad del criterio J(θ) = ||y − Xθ||² ---
    # 1er orden: ∇J = −2·Xᵀ r = 0   (ecuaciones normales)
    gradiente = -2 * X.T @ residuos
    # 2º orden: ∇²J = 2·XᵀX definida positiva  =>  mínimo global único
    autovalores_hessiano = np.linalg.eigvalsh(2 * XtX)

    return {
        "theta": theta,
        "residuos": residuos,
        "sse": sse,
        "s2": s2,
        "s": math.sqrt(s2),
        "n": n,
        "p": p,
        "gl": gl,
        "cov": cov,
        "XtX_inv": XtX_inv,
        "error_estandar": np.sqrt(np.diag(cov)),
        "diagnostico": {
            # Gradiente relativo: |∇J| dividido por la escala de X y de los residuos,
            # para que no dependa de las unidades. ≈ 0 indica que se llegó al óptimo.
            "gradiente_relativo": float(
                np.max(np.abs(gradiente / 2))
                / (np.linalg.norm(X, 2) * max(np.linalg.norm(residuos), 1e-300))
            ),
            "autovalor_min_hessiano": float(autovalores_hessiano.min()),
            # Confiabilidad numérica: si cond(X) es enorme, (XᵀX)⁻¹ pierde precisión.
            "numero_condicion_X": float(np.linalg.cond(X)),
        },
    }


def intervalo_prediccion(X0, ajuste):
    """
    Intervalo de predicción al 95 % de una NUEVA observación en las filas X0:

        ŷ0 ± t(gl) · s · sqrt(1 + x0ᵀ (XᵀX)⁻¹ x0)      (t de la tabla t)

    Devuelve (y_hat, semiancho).
    """
    X0 = np.atleast_2d(np.asarray(X0, dtype=float))
    y_hat = X0 @ ajuste["theta"]
    apalancamiento = np.einsum("ij,jk,ik->i", X0, ajuste["XtX_inv"], X0)
    semiancho = t_tabla(ajuste["gl"]) * ajuste["s"] * np.sqrt(1 + apalancamiento)
    return y_hat, semiancho


def rmse(error):
    error = np.asarray(error, dtype=float)
    return float(np.sqrt(np.mean(error ** 2)))
