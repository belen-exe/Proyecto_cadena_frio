# Memoria de cálculo R1 — Circuito de acondicionamiento

> Generado por `0_diseno/diseno_circuito.py`. Valores calculados con los datos nominales.

## 1. Diagrama del circuito

![Diagrama](esquematico.png)

Cada canal es un divisor de voltaje: `3V3 ── R_fijo ── nodo ── NTC ── GND`, y el nodo
va a un pin del ADC del ESP32 (GPIO34, GPIO35, GPIO32). El LED de alarma va en GPIO2
con un resistor de 220 Ω.

## 2. Datos

| Dato | Valor |
|---|---|
| NTC | R0 = 10 kΩ a 25 °C, β = 3950 K |
| Alimentación | Vcc = 3,3 V |
| ADC | 12 bits (0–4095 cuentas) |
| Rango de operación | 0 a 40 °C |

Ecuaciones:

- NTC: R(T) = R0 · e^(β·(1/T − 1/298,15)), con T en kelvin.
- Divisor: V = Vcc · R(T) / (R_fijo + R(T)).
- ADC: cuenta = V / Vcc · 4095.

## 3. Cálculo del resistor fijo

**Criterio:** elegir el R_fijo que dé la mayor variación de voltaje entre 0 y 40 °C,
ΔV = V(0 °C) − V(40 °C). Más variación significa más cuentas del ADC para el mismo
rango, es decir, mejor resolución.

**Paso 1.** Resistencia del NTC en los extremos del rango:
R(0 °C) = 33621 Ω y R(40 °C) = 5301 Ω.

**Paso 2.** Al derivar ΔV respecto a R_fijo e igualar a cero se obtiene:

R_fijo* = √(R(0 °C) · R(40 °C)) = √(33621 · 5301) = **13351 Ω**

**Paso 3.** Comparación de valores comerciales (ΔV óptimo = 1.424 V):

| R_fijo | V(0 °C) [V] | V(40 °C) [V] | ΔV [V] | % del óptimo |
|---|---|---|---|---|
| 8.2 kΩ | 2.653 | 1.296 | 1.357 | 95.3 % |
| 10 kΩ | 2.543 | 1.143 | 1.400 | 98.3 % |
| 12 kΩ | 2.432 | 1.011 | 1.421 | 99.8 % |
| 15 kΩ | 2.282 | 0.862 | 1.420 | 99.7 % |
| 18 kΩ | 2.149 | 0.751 | 1.398 | 98.2 % |

**Decisión: R_fijo = 10 kΩ.** El mejor valor comercial sería 12 kΩ, pero el
módulo NTC de Wokwi trae 10 kΩ fijo. Con 10 kΩ se obtiene el 98.3 % de la
variación óptima, una pérdida despreciable.

## 4. Resolución en °C por cuenta del ADC (R_fijo = 10 kΩ)

Resolución = 1 / |dADC/dT|, con

dADC/dT = 4095 · R_fijo · (dR/dT) / (R_fijo + R)²  y  dR/dT = −β · R / T²  (T en kelvin).

| T [°C] | R_NTC [Ω] | V nodo [V] | ADC [cuentas] | Resolución [°C/cuenta] |
|---|---|---|---|---|
| 0 | 33621 | 2.543 | 3156 | **0.0261** |
| 5 | 25925 | 2.381 | 2955 | **0.0238** |
| 20 | 12535 | 1.836 | 2278 | **0.0215** |
| 40 | 5301 | 1.143 | 1419 | **0.0268** |

En todo el rango, una cuenta del ADC equivale a unos 0,02–0,03 °C, mucho menos que la
exactitud pedida en R7 (0,4 °C). La resolución no limita la medición.
