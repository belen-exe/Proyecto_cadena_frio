# E2_calentamiento — Experimento E2 y dinámica térmica

**Estado: PENDIENTE** (solo existe un borrador del "segundo método", ver abajo)

**Requisitos que cubrirá:** R8, R9, R10.

**Entradas:**
- Modelo del sensor de `comun/modelo_sensor.py`.
- Coeficientes de calibración de `E1_calibracion/resultados/`.
- Datos simulados de E2: enfriamiento ≥ 2 h en la nevera y ≥ 45 min a temperatura
  ambiente, con la temperatura ambiente registrada.

**Salidas previstas:**
- `datos/`: datos crudos de E2 (`Origen = SIMULADO`) y descripción del contenedor.
- `resultados/`: parámetros del modelo dinámico estimados con PSO propio y con un
  segundo método, intervalo al 95 % de la rapidez de calentamiento, gráficas de
  datos vs. modelo y de residuos, y los cálculos de diseño del vehículo (R10).

**Archivo existente:**
- `metodo2_regresion.py`: borrador del segundo método (regresión matricial de
  T(t) a partir de T(t−1), el ambiente y la tapa). Hoy usa los datos de 24 h del
  simulador anterior (`archivo/datos_modelo_termico.csv`); falta adaptarlo a E2.
