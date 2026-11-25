# Resumen — Planeación de rutas (R15–R18)

Formulación matemática (R15): ver `rutas/formulacion.md`.
Costo de un plan = M·(número de rutas) + distancia total [km], con M = 1000.
Tiempo de una ruta = km / 0,5 km/min + 8 min por cliente ≤ 150 min.

## R16 — Validación frente al óptimo exacto

**Instancia reducida:** depósito + clientes 1 a 8 (mismas coordenadas y reglas que el caso completo).
**Método exacto:** fuerza bruta. Se prueban los 8! = 40 320 órdenes de visita; cada orden se
corta en rutas de la mejor forma posible (programación dinámica sobre los puntos de corte).
Todo plan es algún orden cortado en rutas, así que el mejor de todos es el óptimo.
Hormigas con la configuración inicial (α = 1.0, β = 2.0, ρ = 0.1),
10 hormigas, 60 iteraciones.

| Método | Rutas | Distancia [km] | Costo | Brecha vs óptimo [%] | Plan |
|---|---|---|---|---|---|
| Óptimo exacto (fuerza bruta) | 2 | 77.92 | 2077.92 | 0.00 | 0-1-3-8-6-7-0 ; 0-2-5-4-0  |
| Voraz (vecino más cercano) | 2 | 96.01 | 2096.01 | 0.87 | 0-2-5-4-7-8-3-0 ; 0-1-6-0  |
| Hormigas, mejor de 20 corridas | 2 | 77.92 | 2077.92 | 0.00 | 0-7-6-8-3-1-0 ; 0-2-5-4-0  |
| Hormigas, promedio de 20 corridas |  | 78.12 | 2078.12 | 0.01 |  11 de 20 corridas llegan al óptimo |

## R17 — Ajuste de hiperparámetros con abejas

Hiperparámetros y rangos: alfa ∈ [0.5, 3.0], beta ∈ [1.0, 6.0], rho ∈ [0.05, 0.6].
Algoritmo de abejas: 6 exploradoras, 2 mejores sitios con 2 reclutas cada uno,
4 ciclos, vecindario inicial 25 % del rango que se reduce ×0.7 por ciclo.
Calidad de una configuración = costo promedio de 20 corridas independientes del ACO
(semillas 0–19). Mejor costo medio por ciclo: 2953.15, 2801.34, 2597.65, 2597.65, 2597.65.

Comparación final con 20 corridas NUEVAS (semillas 100–119, no usadas en el ajuste),
14 clientes. Mejor solución conocida = la mejor encontrada en todas estas corridas y el voraz:
costo 2091.62 (2 rutas, 91.62 km).

| Configuración | α | β | ρ | Costo medio | Desv. estándar | Alcanzan la mejor conocida | Con 2 rutas |
|---|---|---|---|---|---|---|---|
| Inicial (sin ajustar) | 1.00 | 2.00 | 0.100 | 2748.97 | 494.57 | 0 % | 35 % |
| Ajustada (abejas) | 1.51 | 1.99 | 0.100 | 2699.00 | 508.12 | 5 % | 40 % |

**Conclusión:** el ajuste MEJORÓ el desempeño de las hormigas
(costo medio 2748.97 → 2699.00). Como cada ruta extra suma
M = 1000, el costo medio refleja sobre todo qué fracción de corridas logra el menor número de rutas.

## R18 — Plan de rutas para los 14 clientes

Mejor plan de las 20 corridas con la configuración ajustada. Figura: `plan_rutas.png`.

| Ruta | Secuencia | Clientes | Distancia [km] | Duración [min] |
|---|---|---|---|---|
| 1 | 0 → 11 → 5 → 4 → 12 → 10 → 9 → 13 → 2 → 0 | 8 | 42.78 | 149.6 |
| 2 | 0 → 7 → 6 → 8 → 3 → 1 → 14 → 0 | 6 | 48.84 | 145.7 |

- **Número de rutas: 2.** Distancia total: **91.62 km**.
  Brecha respecto de la mejor solución conocida: **0.00 %**.
- Todas las rutas duran ≤ 150 min y cada cliente aparece exactamente una vez (verificado en el código).
- **¿Podría hacerse con 1 ruta?** No: una ruta con los 14 clientes pasaría por los clientes 6 y 12,
  así que viajaría al menos 0 → 6 → 12 → 0 (desigualdad triangular) y duraría como mínimo
  221 min > 150 min. Por lo tanto 2 rutas es el mínimo posible.
- Como referencia, el voraz necesita 3 rutas y 121.32 km.
