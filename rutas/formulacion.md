# R15 — Formulación matemática del problema de rutas

## Conjuntos y datos

| Símbolo | Significado |
|---|---|
| N = {0, 1, …, 14} | puntos: 0 es el depósito, 1–14 los clientes |
| C = {1, …, 14} | clientes |
| K = {1, …, 14} | rutas posibles (como mucho una por cliente; no hay límite de vehículos) |
| d_ij | distancia por carretera de i a j [km] = 1,3 × √((x_i − x_j)² + (y_i − y_j)²) |
| t_ij | tiempo de viaje de i a j [min] = d_ij / 0,5 km/min = 2·d_ij |
| s_j | tiempo de servicio [min]: s_j = 8 si j es cliente, s_0 = 0 |
| L | duración máxima de una ruta = 150 min |
| M | penalización por ruta = 1000 (mayor que la distancia de cualquier plan) |

## Variables

| Variable | Tipo | Significado |
|---|---|---|
| x_ijk | binaria (0 o 1) | 1 si la ruta k va directamente del punto i al punto j |
| y_k | binaria (0 o 1) | 1 si la ruta k se usa |

## Función objetivo

    min  M · Σ_k y_k  +  Σ_k Σ_i Σ_j d_ij · x_ijk

El primer término cuenta las rutas y el segundo suma los km. Como M es mayor que la
distancia de cualquier plan, quitar una ruta siempre baja más el costo que cualquier
ahorro de km: se minimiza **primero el número de rutas** y, entre planes con el mismo
número, **la distancia total** (prioridades de R18).

## Restricciones

1. **Cada cliente se visita exactamente una vez, en una sola ruta:**

       Σ_k Σ_i x_ijk = 1                      para todo cliente j ∈ C

2. **Lo que entra sale** (una ruta que llega a un punto también sale de él):

       Σ_i x_ihk = Σ_j x_hjk                  para todo punto h ∈ N y toda ruta k

3. **Cada ruta usada sale una vez del depósito** (y, por la restricción 2, vuelve a él):

       Σ_j x_0jk = y_k                        para toda ruta k

4. **Duración máxima** (viaje + servicio ≤ 150 min):

       Σ_i Σ_j (t_ij + s_j) · x_ijk ≤ L · y_k     para toda ruta k

5. **Sin subtours** (ningún ciclo que no pase por el depósito):

       Σ_{i∈S} Σ_{j∈S} x_ijk ≤ |S| − 1         para todo subconjunto S ⊆ C con |S| ≥ 2 y toda ruta k

6. **Sin tramos de un punto a sí mismo:** x_iik = 0.

Con estas restricciones, toda solución que las cumpla es un plan válido: cada cliente
atendido una vez, cada ruta empieza y termina en el depósito, sin ciclos sueltos y
con duración ≤ 150 min.

## Cómo se usa en el código (`problema.py`)

- Un plan se guarda como lista de rutas, p. ej. `[[11, 5, 4], [7, 6, 8]]`; así las
  restricciones 2, 3, 5 y 6 se cumplen por construcción (cada ruta es una secuencia
  que sale y vuelve al depósito).
- La restricción 1 y la 4 se verifican con `es_factible(plan, clientes)`.
- La función objetivo es `costo(plan) = M·len(plan) + km`.
