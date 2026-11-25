"""
Datos del caso de rutas (Sección 7 del enunciado) y funciones básicas:
distancias, tiempos, costo de un plan, algoritmo voraz y fuerza bruta.

Un PLAN es una lista de rutas; cada ruta es una lista de clientes (números 1..14)
en el orden en que se visitan. El depósito (punto 0) no se escribe: toda ruta
sale de él y vuelve a él.
    Ejemplo: [[3, 8, 7], [2, 13, 9]]  ->  0→3→8→7→0  y  0→2→13→9→0
"""

from itertools import permutations

import numpy as np

# ==========================================
# DATOS (Sección 7)
# ==========================================

# Punto 0 = depósito; puntos 1..14 = clientes. Coordenadas en km.
COORDENADAS = np.array([
    [10.0, 10.0],   # 0 depósito
    [3.6, 12.8],    # 1
    [9.3, 7.4],     # 2
    [7.1, 15.8],    # 3
    [18.1, 3.5],    # 4
    [13.1, 6.0],    # 5
    [19.3, 18.4],   # 6
    [12.7, 15.1],   # 7
    [10.3, 16.5],   # 8
    [9.0, 6.8],     # 9
    [5.6, 4.5],     # 10
    [10.5, 8.6],    # 11
    [13.3, 0.3],    # 12
    [9.0, 7.3],     # 13
    [3.9, 11.9],    # 14
])

FACTOR_CARRETERA = 1.3        # distancia por carretera = 1,3 × euclidiana
VELOCIDAD_KM_MIN = 30 / 60    # 30 km/h = 0,5 km/min  ->  2 min por km
SERVICIO_MIN = 8.0            # descarga y registro en cada cliente
DURACION_MAX_MIN = 150.0      # duración máxima de una ruta

# Penalización por ruta en la función objetivo: costo = M·(número de rutas) + distancia.
# M es mayor que la distancia de CUALQUIER plan (el peor, 14 rutas de ida y vuelta,
# no llega a 600 km), así que una ruta menos siempre vale más que cualquier ahorro
# de distancia. Así queda la prioridad de R18: primero rutas, luego distancia.
M_POR_RUTA = 1000.0

# Matriz de distancias por carretera [km]: D[i, j] entre los puntos i y j.
diferencia = COORDENADAS[:, None, :] - COORDENADAS[None, :, :]
D = FACTOR_CARRETERA * np.sqrt((diferencia ** 2).sum(axis=2))

# Matriz de tiempos de viaje [min]
T_VIAJE = D / VELOCIDAD_KM_MIN

# ==========================================
# EVALUAR UN PLAN
# ==========================================


def distancia_ruta(ruta):
    """km de 0 → ruta[0] → … → ruta[-1] → 0."""
    puntos = [0] + list(ruta) + [0]
    return float(sum(D[a, b] for a, b in zip(puntos[:-1], puntos[1:])))


def duracion_ruta(ruta):
    """min de viaje + servicio de cada cliente."""
    return distancia_ruta(ruta) / VELOCIDAD_KM_MIN + SERVICIO_MIN * len(ruta)


def costo(plan):
    """Función objetivo: M·(número de rutas) + distancia total."""
    return M_POR_RUTA * len(plan) + sum(distancia_ruta(r) for r in plan)


def es_factible(plan, clientes):
    """Cada cliente exactamente una vez y cada ruta ≤ 150 min."""
    visitados = sorted(c for r in plan for c in r)
    return visitados == sorted(clientes) and all(
        duracion_ruta(r) <= DURACION_MAX_MIN + 1e-9 for r in plan)


def cabe(tiempo_actual, actual, siguiente):
    """¿Se puede ir de 'actual' a 'siguiente', atenderlo y volver al depósito a tiempo?"""
    return (tiempo_actual + T_VIAJE[actual, siguiente] + SERVICIO_MIN
            + T_VIAJE[siguiente, 0]) <= DURACION_MAX_MIN + 1e-9


# ==========================================
# ALGORITMO VORAZ (vecino más cercano)
# ==========================================


def voraz(clientes):
    """
    Desde el punto actual se va al cliente MÁS CERCANO que todavía quepa en el
    tiempo de la ruta. Si ninguno cabe, se vuelve al depósito y se abre otra ruta.
    """
    pendientes = set(clientes)
    plan = []
    while pendientes:
        ruta, actual, tiempo = [], 0, 0.0
        while True:
            candidatos = [c for c in pendientes if cabe(tiempo, actual, c)]
            if not candidatos:
                break
            siguiente = min(candidatos, key=lambda c: D[actual, c])
            tiempo += T_VIAJE[actual, siguiente] + SERVICIO_MIN
            ruta.append(siguiente)
            pendientes.remove(siguiente)
            actual = siguiente
        if not ruta:
            raise ValueError("Hay un cliente que no cabe ni en una ruta exclusiva")
        plan.append(ruta)
    return plan


# ==========================================
# MÉTODO EXACTO: FUERZA BRUTA (solo para pocos clientes)
# ==========================================


def mejor_corte(orden):
    """
    Dado un ORDEN de visita de todos los clientes, lo corta en rutas consecutivas
    de la mejor manera posible (menor costo), probando todos los cortes con
    programación dinámica:
        mejor[j] = costo mínimo para atender los primeros j clientes del orden
        mejor[j] = min_i ( mejor[i] + M + km de la ruta orden[i:j] )   si esa ruta cabe
    """
    n = len(orden)
    mejor = [0.0] + [np.inf] * n
    corte = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j):
            ruta = orden[i:j]
            if duracion_ruta(ruta) > DURACION_MAX_MIN + 1e-9:
                continue
            valor = mejor[i] + M_POR_RUTA + distancia_ruta(ruta)
            if valor < mejor[j]:
                mejor[j], corte[j] = valor, i
    # Reconstruir las rutas de atrás hacia adelante
    plan, j = [], n
    while j > 0:
        plan.insert(0, list(orden[corte[j]:j]))
        j = corte[j]
    return mejor[n], plan


def fuerza_bruta(clientes):
    """
    Óptimo EXACTO: prueba TODOS los órdenes posibles de los clientes (n!) y cada
    uno lo corta en rutas de la mejor manera. Todo plan posible es algún orden
    cortado en rutas, así que el mejor de todos es el óptimo.
    Con 8 clientes son 8! = 40 320 órdenes (unos segundos); con 14 serían
    87 mil millones, imposible: por eso solo se usa en la instancia reducida.
    """
    mejor_valor, mejor_plan = np.inf, None
    for orden in permutations(clientes):
        if orden[0] > orden[-1]:
            continue   # un orden y su reverso dan los mismos km: se prueba solo uno
        valor, plan = mejor_corte(orden)
        if valor < mejor_valor:
            mejor_valor, mejor_plan = valor, plan
    return mejor_plan
