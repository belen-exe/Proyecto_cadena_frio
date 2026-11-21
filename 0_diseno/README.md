# 0_diseno — Diseño del circuito de acondicionamiento

**Estado: PENDIENTE**

**Requisitos que cubrirá:** R1 (y el esquemático de R3).

**Entradas:**
- Parámetros nominales del termistor y del ADC definidos en `comun/modelo_sensor.py`
  (R0, β, R_fijo, Vcc, 12 bits).
- Rango de operación: 0 a 40 °C.

**Salidas previstas:**
- Diagrama del circuito de un canal.
- Memoria de cálculo del resistor fijo (criterio de selección explícito).
- Tabla de resolución en °C por cuenta del ADC en al menos tres temperaturas.
