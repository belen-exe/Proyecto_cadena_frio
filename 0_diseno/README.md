# 0_diseno — Diseño del circuito de acondicionamiento (R1)

**Estado: Hecho** (cálculo teórico; el montaje es simulado en Wokwi).

**Requisitos:** R1 y el esquemático de R3.

**Entradas:** parámetros nominales de `comun/modelo_sensor.py` (R0 = 10 kΩ,
β = 3950 K, Vcc = 3,3 V, ADC de 12 bits) y el rango de operación 0–40 °C.

**Ejecución:** `python 0_diseno/diseno_circuito.py`

**Salidas (`resultados/`):**

| Archivo | Contenido |
|---|---|
| `memoria_calculo_R1.md` | Memoria de cálculo completa: criterio, resistor elegido, resolución y comprobaciones |
| `tabla_resolucion.csv` | Resolución en °C por cuenta del ADC en 0, 2, 5, 8, 20, 30 y 40 °C |
| `curvas_divisor.png` | Voltaje del nodo vs temperatura para varios R_fijo |
| `resolucion.png` | °C por cuenta vs temperatura (10 kΩ y el E12 óptimo) |
| `esquematico.png` | Esquemático completo: 3 canales NTC + LED de alarma |

**Resumen del resultado:**
- Criterio: maximizar la excursión de voltaje ΔV = V(0 °C) − V(40 °C), cuyo óptimo
  es R_fijo* = √(R_ntc(0 °C)·R_ntc(40 °C)) ≈ 13,4 kΩ (E12 más cercano: 12 kΩ).
- Valor adoptado: **10 kΩ**, impuesto por el módulo NTC de Wokwi; conserva el
  98,3 % de la excursión óptima.
- Resolución con 10 kΩ: ≈ 0,023–0,027 °C por cuenta en 0–40 °C.
