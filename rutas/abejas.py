"""
Algoritmo de abejas (Bees Algorithm), implementación PROPIA (R17).

Busca los mejores hiperparámetros (α, β, ρ) de las hormigas. Cada "flor" es una
configuración (α, β, ρ) y su calidad es el COSTO PROMEDIO de 20 corridas
independientes del ACO con esa configuración (menor = mejor).

  1. Exploradoras: NUM_EXPLORADORAS configuraciones al azar dentro de los rangos.
  2. Repetir NUM_CICLOS veces:
     a. se eligen las NUM_SITIOS mejores flores;
     b. a cada una se envían NUM_RECLUTAS abejas que prueban configuraciones
        cercanas (dentro de un vecindario); si alguna es mejor, reemplaza a la flor;
     c. el resto de exploradoras busca otra vez al azar (evita quedarse en un solo lugar);
     d. el vecindario se achica (se afina la búsqueda alrededor de lo bueno).
"""

import numpy as np

import hormigas as aco

RANGOS = {"alfa": (0.5, 3.0), "beta": (1.0, 6.0), "rho": (0.05, 0.6)}
NUM_EXPLORADORAS = 6
NUM_SITIOS = 2
NUM_RECLUTAS = 2
NUM_CICLOS = 4
VECINDARIO_INICIAL = 0.25     # fracción del ancho de cada rango
REDUCCION_VECINDARIO = 0.7
NUM_CORRIDAS = 20             # corridas del ACO por configuración (R17: ≥ 20)


def evaluar(config, clientes, semillas):
    """Corre el ACO con cada semilla y devuelve la lista de costos."""
    return [aco.hormigas(clientes, config["alfa"], config["beta"], config["rho"], semilla=s)[1]
            for s in semillas]


def al_azar(rng):
    return {k: float(rng.uniform(a, b)) for k, (a, b) in RANGOS.items()}


def vecina(config, tamano, rng):
    """Configuración cercana: cada valor se mueve ± tamano·ancho, sin salir del rango."""
    nueva = {}
    for k, (a, b) in RANGOS.items():
        paso = tamano * (b - a)
        nueva[k] = float(np.clip(config[k] + rng.uniform(-paso, paso), a, b))
    return nueva


def abejas(clientes, semilla=0):
    """
    Devuelve (mejor_config, historia). Todas las configuraciones se evalúan con las
    MISMAS 20 semillas, para que la comparación entre ellas sea justa.
    """
    rng = np.random.default_rng(semilla)
    semillas = list(range(NUM_CORRIDAS))

    def calidad(config):
        return float(np.mean(evaluar(config, clientes, semillas)))

    flores = [al_azar(rng) for _ in range(NUM_EXPLORADORAS)]
    valores = [calidad(f) for f in flores]
    tamano = VECINDARIO_INICIAL
    historia = [min(valores)]

    for ciclo in range(NUM_CICLOS):
        orden = np.argsort(valores)
        nuevas_flores, nuevos_valores = [], []
        # b. reclutas alrededor de los mejores sitios
        for i in orden[:NUM_SITIOS]:
            mejor_f, mejor_v = flores[i], valores[i]
            for _ in range(NUM_RECLUTAS):
                candidata = vecina(flores[i], tamano, rng)
                v = calidad(candidata)
                if v < mejor_v:
                    mejor_f, mejor_v = candidata, v
            nuevas_flores.append(mejor_f)
            nuevos_valores.append(mejor_v)
        # c. el resto vuelve a explorar al azar
        for _ in range(NUM_EXPLORADORAS - NUM_SITIOS):
            f = al_azar(rng)
            nuevas_flores.append(f)
            nuevos_valores.append(calidad(f))
        flores, valores = nuevas_flores, nuevos_valores
        tamano *= REDUCCION_VECINDARIO          # d. vecindario más pequeño
        historia.append(min(valores))
        print(f"  ciclo {ciclo + 1}/{NUM_CICLOS}: mejor costo medio = {min(valores):.2f}")

    i = int(np.argmin(valores))
    return flores[i], historia
