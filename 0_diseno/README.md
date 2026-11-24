# 0_diseno — Diseño del circuito de acondicionamiento (R1)

**Estado: Hecho** (cálculo teórico; el montaje es simulado en Wokwi).

**Ejecución:** `python 0_diseno/diseno_circuito.py`

**Entregables de R1 (en `resultados/`):**

| Entregable de R1 | Archivo |
|---|---|
| Diagrama del circuito | `esquematico.png` |
| Memoria de cálculo del resistor fijo | `memoria_calculo_R1.md` (secciones 2 y 3) |
| Tabla de resolución en °C por cuenta del ADC (0, 5, 20 y 40 °C) | `memoria_calculo_R1.md` (sección 4) y `tabla_resolucion.csv` |

**Resumen:**
- Criterio: máxima variación de voltaje entre 0 y 40 °C, cuyo óptimo es
  R_fijo* = √(R(0 °C)·R(40 °C)) ≈ 13,4 kΩ.
- Valor adoptado: **10 kΩ** (viene fijo en el módulo NTC de Wokwi); da el 98,3 % de
  la variación óptima.
- Resolución: entre 0,022 y 0,027 °C por cuenta del ADC.
