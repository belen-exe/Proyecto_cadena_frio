"""
Optimización por enjambre de partículas (PSO) - implementación PROPIA (R9).

Algoritmo (versión global con peso de inercia decreciente):

    v_i ← w·v_i + c1·r1·(p_i − x_i) + c2·r2·(g − x_i)
    x_i ← x_i + v_i

  x_i : posición de la partícula i (un vector de parámetros)
  v_i : velocidad de la partícula i
  p_i : mejor posición que ha visto la partícula i
  g   : mejor posición que ha visto todo el enjambre
  w   : peso de inercia, baja linealmente de w_inicial a w_final
  c1, c2 : coeficientes cognitivo y social; r1, r2 ~ U(0, 1)

Las posiciones se limitan a la caja [limite_inferior, limite_superior] y las
velocidades a una fracción del ancho de esa caja.
"""

import numpy as np


def pso(
    funcion_costo,
    limite_inferior,
    limite_superior,
    num_particulas=30,
    num_iteraciones=150,
    w_inicial=0.9,
    w_final=0.4,
    c1=2.0,
    c2=2.0,
    fraccion_velocidad_max=0.2,
    semilla=None,
):
    """
    Minimiza funcion_costo(X) donde X es una matriz (num_particulas × dimensión)
    y la función devuelve un vector con el costo de cada fila.

    Devuelve un diccionario con la mejor posición, su costo y la historia del
    mejor costo por iteración (para la gráfica de convergencia).
    """
    rng = np.random.default_rng(semilla)
    inferior = np.asarray(limite_inferior, dtype=float)
    superior = np.asarray(limite_superior, dtype=float)
    dimension = len(inferior)
    ancho = superior - inferior
    v_max = fraccion_velocidad_max * ancho

    # Inicialización uniforme dentro de la caja
    x = inferior + rng.random((num_particulas, dimension)) * ancho
    v = rng.uniform(-v_max, v_max, size=(num_particulas, dimension))

    costo = funcion_costo(x)
    mejor_personal = x.copy()
    costo_personal = costo.copy()
    indice = int(np.argmin(costo_personal))
    mejor_global = mejor_personal[indice].copy()
    costo_global = float(costo_personal[indice])

    historia = [costo_global]

    for iteracion in range(num_iteraciones):
        w = w_inicial - (w_inicial - w_final) * iteracion / max(num_iteraciones - 1, 1)
        r1 = rng.random((num_particulas, dimension))
        r2 = rng.random((num_particulas, dimension))

        v = w * v + c1 * r1 * (mejor_personal - x) + c2 * r2 * (mejor_global - x)
        v = np.clip(v, -v_max, v_max)
        x = np.clip(x + v, inferior, superior)

        costo = funcion_costo(x)
        mejora = costo < costo_personal
        mejor_personal[mejora] = x[mejora]
        costo_personal[mejora] = costo[mejora]

        indice = int(np.argmin(costo_personal))
        if costo_personal[indice] < costo_global:
            costo_global = float(costo_personal[indice])
            mejor_global = mejor_personal[indice].copy()

        historia.append(costo_global)

    return {
        "mejor_posicion": mejor_global,
        "mejor_costo": costo_global,
        "historia": np.array(historia),
    }


if __name__ == "__main__":
    # Autoprueba: función de Rosenbrock (mínimo en (1, 1) con costo 0).
    def rosenbrock(X):
        return (1 - X[:, 0]) ** 2 + 100 * (X[:, 1] - X[:, 0] ** 2) ** 2

    r = pso(rosenbrock, [-2, -2], [2, 2], num_iteraciones=300, semilla=0)
    print(f"Rosenbrock: x* = {r['mejor_posicion']}, costo = {r['mejor_costo']:.2e}")
