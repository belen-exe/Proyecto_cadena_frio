# rutas — Planeación de rutas de distribución (R15–R18)

**Estado: Hecho.** Es independiente del resto del proyecto: solo usa las coordenadas
y las reglas de la Sección 7 del enunciado (no hay datos simulados aquí).

## Cómo ejecutarlo (desde la raíz del repositorio)

```bash
python rutas/planear_rutas.py     # R16, R17 y R18 (tarda unos 3–4 minutos, casi todo en R17)
```

La formulación de R15 está escrita en `formulacion.md` (no se ejecuta).

## Archivos

| Archivo | Qué es |
|---|---|
| `formulacion.md` | R15: variables, función objetivo y restricciones |
| `problema.py` | Coordenadas, distancias (1,3 × euclidiana), tiempos (2 min/km + 8 min por cliente), costo de un plan, algoritmo **voraz** y **fuerza bruta** |
| `hormigas.py` | Algoritmo de colonia de hormigas (implementación propia) |
| `abejas.py` | Algoritmo de abejas que ajusta α, β y ρ de las hormigas (implementación propia) |
| `planear_rutas.py` | Corre todo y escribe los resultados |
| `resultados/resumen_rutas.md` | Tablas de R16, R17 y R18 |
| `resultados/plan_rutas.png` | Mapa del plan final |

## La idea en una frase

Las hormigas resuelven el problema, el voraz y la fuerza bruta demuestran que lo
resuelven bien, y las abejas lo afinan.

- **Costo de un plan** = 1000 × (número de rutas) + km. El 1000 hace que una ruta
  menos siempre gane, y entre planes con igual número de rutas gana el de menos km.
- **Voraz:** ir siempre al cliente más cercano que quepa en los 150 min; si ninguno
  cabe, volver al depósito y abrir otra ruta.
- **Hormigas:** igual que el voraz, pero el siguiente cliente se elige al azar con
  probabilidad ∝ feromona^α × (1/distancia)^β. La feromona se evapora (ρ) y la mejor
  hormiga refuerza sus tramos, así la colonia aprende.
- **Fuerza bruta (instancia de 8 clientes):** probar los 8! órdenes posibles y cortar
  cada uno en rutas de la mejor forma. Da el óptimo exacto.
- **Abejas:** prueban configuraciones (α, β, ρ); cada una se califica con el costo
  promedio de 20 corridas de las hormigas. Buscan más cerca de las mejores y siguen
  explorando al azar con el resto.

## Qué revisar para saber que funciona

- R16: las hormigas llegan al óptimo de la instancia reducida (brecha 0 %) y el voraz queda cerca (≈ 0,9 %).
- R17: la tabla inicial vs ajustada muestra si el costo medio bajó.
- R18: el plan final tiene **2 rutas**, cada una ≤ 150 min, y el resumen demuestra que
  con 1 ruta es imposible (duraría al menos 221 min).
