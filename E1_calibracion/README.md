# E1_calibracion — Experimento E1 y calibración ADC → temperatura

**Estado: PENDIENTE**

**Requisitos que cubrirá:** R4, R5, R6, R7.

**Entradas:**
- Modelo del sensor de `comun/modelo_sensor.py` (para generar las lecturas ADC simuladas).
- Temperaturas de referencia de 0 a 45 °C (simuladas) con la incertidumbre declarada
  del termómetro de referencia.

**Salidas previstas:**
- `datos/`: datos crudos de E1 (≥ 24 puntos de calibración y ≥ 8 de prueba por canal),
  con columna `Origen = SIMULADO`.
- `resultados/`: coeficientes de calibración por canal con su incertidumbre, tabla
  comparativa de estructuras de modelo y tabla de RMSE (0–45 °C y 0–10 °C).
- Los coeficientes serán la entrada de E2, E3 y del firmware (R19).
