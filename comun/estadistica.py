"""
Herramientas estadísticas PROPIAS, usadas por E1 (calibración) y E2 (identificación).

- ajustar_mco: mínimos cuadrados ordinarios con álgebra matricial propia (QR),
  usando solo primitivas de numpy.linalg (qr, solve, inv, svd, eigvalsh, cond).
  No usa funciones que hagan la regresión completa (lstsq, pinv, polyfit).
- t_cuantil: cuantil de la distribución t de Student, calculado por integración
  numérica de su densidad + bisección (así no se necesita scipy).
"""

import math

import numpy as np

# ==========================================
# 1. DISTRIBUCIÓN t DE STUDENT
# ==========================================


def t_densidad(x, gl):
    """Densidad de la t de Student con gl grados de libertad."""
    constante = math.exp(math.lgamma((gl + 1) / 2) - math.lgamma(gl / 2)) / math.sqrt(gl * math.pi)
    return constante * (1 + np.asarray(x, dtype=float) ** 2 / gl) ** (-(gl + 1) / 2)


def t_acumulada(x, gl, puntos=4001):
    """P(T ≤ x) por regla de Simpson entre 0 y |x| (la densidad es simétrica)."""
    if x == 0:
        return 0.5
    malla = np.linspace(0.0, abs(x), puntos)
    f = t_densidad(malla, gl)
    h = malla[1] - malla[0]
    integral = h / 3 * (f[0] + f[-1] + 4 * f[1:-1:2].sum() + 2 * f[2:-1:2].sum())
    return 0.5 + math.copysign(integral, x)


def t_cuantil(p, gl, tolerancia=1e-8):
    """Valor x tal que P(T ≤ x) = p, por bisección (0.5 < p < 1)."""
    if not 0.5 < p < 1:
        raise ValueError("p debe estar entre 0.5 y 1")
    bajo, alto = 0.0, 1000.0
    while alto - bajo > tolerancia:
        medio = (bajo + alto) / 2
        if t_acumulada(medio, gl) < p:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


# ==========================================
# 2. MÍNIMOS CUADRADOS ORDINARIOS (implementación propia)
# ==========================================


def ajustar_mco(X, y):
    """
    Resuelve  min_θ ||y − Xθ||²  mediante la factorización QR:

        X = Q R   =>   R θ = Qᵀ y

    Devuelve un diccionario con:
        theta, residuos, s2 (varianza residual), gl (n − p), cov (s²·(XᵀX)⁻¹),
        error_estandar, y diagnósticos de optimalidad y de confiabilidad numérica.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    if n <= p:
        raise ValueError("Se necesitan más observaciones que parámetros")

    # --- Solución principal: QR ---
    Q, R = np.linalg.qr(X)
    theta = np.linalg.solve(R, Q.T @ y)

    residuos = y - X @ theta
    sse = float(residuos @ residuos)
    gl = n - p
    s2 = sse / gl

    XtX = X.T @ X
    XtX_inv = np.linalg.inv(XtX)
    cov = s2 * XtX_inv

    # --- Condiciones de optimalidad del criterio J(θ) = ||y − Xθ||² ---
    # 1er orden: ∇J = −2·Xᵀ r = 0   (ecuaciones normales)
    gradiente = -2 * X.T @ residuos
    # 2º orden: ∇²J = 2·XᵀX definida positiva  =>  mínimo global único
    autovalores_hessiano = np.linalg.eigvalsh(2 * XtX)

    # --- Confiabilidad numérica: otros dos caminos deben dar lo mismo ---
    theta_normales = np.linalg.solve(XtX, X.T @ y)          # ecuaciones normales
    U, S, Vt = np.linalg.svd(X, full_matrices=False)       # SVD
    theta_svd = Vt.T @ ((U.T @ y) / S)

    escala = np.maximum(np.abs(theta), 1e-300)

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
            "norma_gradiente": float(np.max(np.abs(gradiente))),
            "norma_gradiente_relativa": float(
                np.max(np.abs(X.T @ residuos))
                / (np.linalg.norm(X, 2) * max(np.linalg.norm(residuos), 1e-300))
            ),
            "autovalor_min_hessiano": float(autovalores_hessiano.min()),
            "autovalor_max_hessiano": float(autovalores_hessiano.max()),
            "numero_condicion_X": float(np.linalg.cond(X)),
            "numero_condicion_XtX": float(np.linalg.cond(XtX)),
            "dif_rel_max_QR_vs_normales": float(np.max(np.abs(theta - theta_normales) / escala)),
            "dif_rel_max_QR_vs_SVD": float(np.max(np.abs(theta - theta_svd) / escala)),
        },
    }


def intervalo_prediccion(X0, ajuste, confianza=0.95):
    """
    Intervalo de predicción de una NUEVA observación en las filas X0:

        ŷ0 ± t(1−α/2, gl) · s · sqrt(1 + x0ᵀ (XᵀX)⁻¹ x0)

    Devuelve (y_hat, semiancho).
    """
    X0 = np.atleast_2d(np.asarray(X0, dtype=float))
    y_hat = X0 @ ajuste["theta"]
    apalancamiento = np.einsum("ij,jk,ik->i", X0, ajuste["XtX_inv"], X0)
    t = t_cuantil(0.5 + confianza / 2, ajuste["gl"])
    semiancho = t * ajuste["s"] * np.sqrt(1 + apalancamiento)
    return y_hat, semiancho


def rmse(error):
    error = np.asarray(error, dtype=float)
    return float(np.sqrt(np.mean(error ** 2)))


if __name__ == "__main__":
    # Autoprueba rápida de los cuantiles t (valores de tabla entre paréntesis).
    for gl, tabla in [(5, 2.5706), (26, 2.0555), (100, 1.9840)]:
        print(f"t(0.975, {gl}) = {t_cuantil(0.975, gl):.4f}  (tabla {tabla})")
