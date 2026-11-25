"""
Algoritmo de colonia de hormigas (ACO), implementación PROPIA (R16).

Cada hormiga arma un plan completo:
  - está en un punto (al principio, el depósito) y elige el siguiente cliente
    SOLO entre los que todavía caben en el tiempo de la ruta, con probabilidad

        P(j) = τ[i,j]^α · η[i,j]^β  /  Σ (lo mismo para todos los candidatos)

        τ[i,j] : feromona del tramo i→j (lo que aprendió la colonia)
        η[i,j] = 1 / D[i,j] : visibilidad (los clientes cercanos son más atractivos)
        α, β   : cuánto pesa la feromona y cuánto la cercanía

  - si ningún cliente cabe, vuelve al depósito y empieza una ruta nueva.

Al terminar cada iteración:
  1. evaporación:  τ ← (1 − ρ)·τ    (se olvida un poco lo anterior)
  2. refuerzo: la MEJOR hormiga encontrada hasta ahora deposita feromona en sus
     tramos, más cuanto mejor es su plan:  τ[i,j] += costo_voraz / costo_mejor
     (vale ≈ 1 si iguala al voraz y más si lo mejora).
"""

import numpy as np

import problema as pb

CONFIG_INICIAL = {"alfa": 1.0, "beta": 2.0, "rho": 0.1}   # valores típicos de los libros
NUM_HORMIGAS = 10
NUM_ITERACIONES = 60


def construir_plan(clientes, tau, alfa, beta, rng):
    """Una hormiga construye un plan completo."""
    pendientes = list(clientes)
    plan = []
    while pendientes:
        ruta, actual, tiempo = [], 0, 0.0
        while True:
            candidatos = [c for c in pendientes if pb.cabe(tiempo, actual, c)]
            if not candidatos:
                break
            atractivo = np.array([tau[actual, c] ** alfa * (1 / pb.D[actual, c]) ** beta
                                  for c in candidatos])
            siguiente = candidatos[rng.choice(len(candidatos), p=atractivo / atractivo.sum())]
            tiempo += pb.T_VIAJE[actual, siguiente] + pb.SERVICIO_MIN
            ruta.append(siguiente)
            pendientes.remove(siguiente)
            actual = siguiente
        plan.append(ruta)
    return plan


def hormigas(clientes, alfa, beta, rho, semilla=None,
             num_hormigas=NUM_HORMIGAS, num_iteraciones=NUM_ITERACIONES):
    """Devuelve (mejor_plan, mejor_costo)."""
    rng = np.random.default_rng(semilla)
    costo_referencia = pb.costo(pb.voraz(clientes))
    tau = np.ones_like(pb.D)            # feromona inicial igual en todos los tramos

    mejor_plan, mejor_costo = None, np.inf
    for _ in range(num_iteraciones):
        for _ in range(num_hormigas):
            plan = construir_plan(clientes, tau, alfa, beta, rng)
            valor = pb.costo(plan)
            if valor < mejor_costo:
                mejor_plan, mejor_costo = plan, valor

        tau *= (1 - rho)                                   # 1. evaporación
        deposito = costo_referencia / mejor_costo          # 2. refuerzo
        for ruta in mejor_plan:
            puntos = [0] + ruta + [0]
            for a, b in zip(puntos[:-1], puntos[1:]):
                tau[a, b] += deposito
                tau[b, a] += deposito                      # la distancia es simétrica
    return mejor_plan, mejor_costo
