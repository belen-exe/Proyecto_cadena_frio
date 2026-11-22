# Memoria de cálculo R1 — Circuito de acondicionamiento

> Generado automáticamente por `0_diseno/diseno_circuito.py`. Valores **CALCULADOS**
> con los parámetros nominales (R0 = 10000 Ω, β = 3950 K, Vcc = 3.3 V, ADC de 12 bits).

## 1. Circuito de cada canal

```
3V3 ──[ R_fijo ]──┬──[ NTC ]── GND
                  └──> GPIO (ADC1)
```

V(T) = Vcc · R_ntc(T) / (R_fijo + R_ntc(T)),  con  R_ntc(T) = R0 · exp(β · (1/T_K − 1/298,15)).

Esquemático completo: `resultados/esquematico.png`.

## 2. Selección del resistor fijo

**Criterio:** maximizar la excursión de voltaje en el rango de operación,
ΔV = V(0 °C) − V(40 °C). Derivando respecto a R_fijo e igualando a cero:

R_fijo* = √( R_ntc(0 °C) · R_ntc(40 °C) ) = √( 33621 Ω · 5301 Ω ) = **13351 Ω**

El valor comercial E12 con mayor excursión es **12 kΩ**.

| Candidato | R_fijo [Ω] | V(0 °C) [V] | V(40 °C) [V] | ΔV [V] | ΔV / ΔV* [%] | Cuentas en 0–40 °C | Resolución media [°C/cuenta] |
|---|---|---|---|---|---|---|---|
| Óptimo teórico | 13351 | 2.362 | 0.938 | 1.424 | 100.0 | 1767 | 0.0226 |
| E12 más cercano (12 kohm) | 12000 | 2.432 | 1.011 | 1.421 | 99.8 | 1763 | 0.0227 |
| Wokwi / adoptado (10 kohm) | 10000 | 2.543 | 1.143 | 1.400 | 98.3 | 1737 | 0.0230 |

**Valor adoptado: 10 kΩ.** El módulo NTC de Wokwi trae el resistor fijo interno de
10 kΩ y no se puede cambiar. Con 10 kΩ se conserva el
98.3 % de la excursión óptima, así que
la pérdida de resolución frente al óptimo es pequeña. En un montaje físico se usaría
12 kΩ.

## 3. Resolución en °C por cuenta del ADC

Sensibilidad: dV/dT = Vcc · R_fijo · (dR/dT) / (R_fijo + R)², con dR/dT = −β·R/T_K².
Cuentas/°C = |dV/dT| · 4095 / Vcc; resolución = 1 / (cuentas/°C).

| T [°C] | R_ntc [Ω] | V nodo [V] | ADC [cuentas] | Cuentas/°C | Resolución 10 kΩ [°C/cuenta] | Resolución 12 kΩ [°C/cuenta] |
|---|---|---|---|---|---|---|
| 0 | 33621 | 2.543 | 3156 | 38.3 | 0.0261 | 0.0238 |
| 2 | 30266 | 2.480 | 3078 | 39.9 | 0.0251 | 0.0230 |
| 5 | 25925 | 2.381 | 2955 | 42.0 | 0.0238 | 0.0221 |
| 8 | 22279 | 2.278 | 2826 | 43.8 | 0.0229 | 0.0215 |
| 20 | 12535 | 1.836 | 2278 | 46.5 | 0.0215 | 0.0213 |
| 30 | 8037 | 1.470 | 1825 | 43.5 | 0.0230 | 0.0237 |
| 40 | 5301 | 1.143 | 1419 | 37.3 | 0.0268 | 0.0285 |

- En la zona crítica 2–8 °C, con 10 kΩ, la resolución va de 0.0229 a
  0.0251 °C/cuenta.
- Comprobación por diferencias finitas: diferencia máxima con la fórmula analítica
  = 2.8e-07 °C/cuenta.
- La resolución por cuantización es mucho menor que la meta de exactitud de R7
  (0,4 °C entre 0 y 10 °C): el error dominante será el ruido y la calibración, no los bits.

## 4. Comprobaciones del diseño (10 kΩ)

| Comprobación | Valor | Comentario |
|---|---|---|
| Rango de voltaje 0–40 °C | 1.143 – 2.543 V | dentro de la zona lineal aproximada del ADC del ESP32 (0.15–3.1 V) |
| Rango de cuentas 0–40 °C | 1419 – 3156 | lejos de 0 y 4095; una lectura ≥ 4090 indica desconexión |
| Corriente máxima del divisor (40 °C) | 0.216 mA | despreciable para el regulador de 3V3 |
| Potencia máxima en el NTC (R_ntc = R_fijo) | 0.272 mW | P = Vcc² / (4·R_fijo) |
| Autocalentamiento máximo | 0.18 °C | con constante de disipación 1.5 mW/°C (típica, supuesta); Wokwi no lo simula. La calibración de E1 absorbe la parte constante |
| Corriente del LED de alarma | 6.8 mA | (3,3 V − 1.8 V) / 220 Ω, menor que 20 mA por pin |

Se usan solo pines del ADC1 (GPIO34, 35, 32) porque el ADC2 del ESP32 no se puede
usar cuando el Wi-Fi está activo; así el diseño no depende de esa condición.
