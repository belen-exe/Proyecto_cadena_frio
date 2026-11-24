# Resultados R10 — Condiciones de diseño del vehículo

> Generado por `E2_calentamiento/diseno_vehiculo.py` a partir del modelo de R9 y la
> descripción del contenedor de R8. Datos **SIMULADOS**.

Condiciones: T_amb = 30 °C, T0 = 4 °C, T_lím = 8 °C, ruta de
150 min, factor de seguridad 1.2 sobre el tiempo.

Modelo (R9, ambiente constante): T(t) = T_amb − (T_amb − T0)·e^(−k·t)  ⇒
t_lím = (1/k)·ln[(T_amb − T0)/(T_amb − T_lím)].

## (i) Rapidez de calentamiento máxima admisible

1. Tiempo que debe resistir: t_req = 1,2 × 150 min = **180 min**.
2. Cociente de diferencias: (30 − 4)/(30 − 8) = 26/22 = 1.1818; ln = 0.1671.
3. k_max = 0.1671 / 180 min = **0.000928 min⁻¹**
   (τ ≥ 1077 min = 18.0 h).

## (ii) Factor de mejora respecto del prototipo

- k del prototipo (R9, PSO): 0.004516 min⁻¹ (τ = 221 min);
  extremo superior del IC 95 %: 0.004693 min⁻¹.
- Con k_proto, la carga llega a 8 °C en 37 min (caso conservador:
  36 min), menos que los 180 min exigidos.
- Factor de mejora = k_proto / k_max = 0.004516 / 0.000928 = **4.87**
  (conservador, con el extremo superior del IC: **5.06**).
  La rapidez de calentamiento debe reducirse ≈ 5.1 veces.

## (iii) Modificación térmica

Modelo físico: k = UA / C.

1. Capacidad térmica (R8): C = 1.0 kg × 4186 J/(kg·K)
   + 0.15 kg × 1300 J/(kg·K) = **4381 J/K**.
2. UA identificado (R9): UA = k·C = (0.004516/60 s⁻¹) × 4381 J/K = **0.3298 W/K**
   (con el extremo superior del IC: 0.3427 W/K).
3. UA teórico de pared plana: A_media = 0.2325 m²;
   UA = 1/[L/(λ·A) + 2/(h·A)] = 1/[0.025/(0.035·0.2325) + 2/(10·0.2325)]
   = **0.2544 W/K**.
4. Factor de puentes térmicos (bordes, tapa): f = 0.3427/0.2544 = **1.347**.
   Sale de los datos; se supone que el rediseño mantiene la misma calidad de cierre.
5. Condición de diseño: k_nuevo = f·UA_teórico(L, λ) / (C + m_geles·4186) ≤ k_max.
   El espesor se resuelve por bisección (dimensiones interiores fijas).

| Opción | Espesor [cm] | λ [W/(m·K)] | Geles extra [kg] | Exterior [cm] | k nuevo [min⁻¹] | τ [min] | t hasta 8 °C [min] | Cumple |
|---|---|---|---|---|---|---|---|---|
| A. Solo pared de icopor más gruesa (mejor posible) | 15.8 | 0.035 | 0.00 | 54×48×46 | 0.002565 | 390 | 65 | no |
| B. Solo pared de poliuretano (mejor posible) | 16.2 | 0.024 | 0.00 | 54×48×46 | 0.001782 | 561 | 94 | no |
| C. Misma caja + geles refrigerantes | 2.5 | 0.035 | 4.25 | 27×21×19 | 0.000928 | 1077 | 180 | sí |
| D. RECOMENDADA: poliuretano 5 cm + geles | 5.0 | 0.024 | 1.70 | 32×26×24 | 0.000911 | 1098 | 183 | sí |

**Solo con aislamiento NO se puede cumplir**
(opciones A y B). Al engrosar la pared de una caja tan pequeña, el área exterior crece casi
tan rápido como la resistencia de la pared, y la convección (2/(h·A)) pone un piso. El
mejor espesor posible deja la carga en 65 min (icopor) y
94 min (poliuretano). Con tan poca carga (1 kg), lo que falta es
**capacidad térmica**. (Para paredes gruesas, el modelo de pared plana con área media es solo
aproximado; aun así la tendencia es clara.)

**Recomendación: opción D.** Una caja de poliuretano de 5 cm, con
1.7 kg de geles refrigerantes preenfriados a 4 °C, llega a 8 °C en
183 min ≥ 180 min. La opción C también cumple, pero
necesita 4.2 kg de geles en la caja actual (más peso y menos espacio para
la carga útil).

Gráfica: `diseno_R10.png`.
