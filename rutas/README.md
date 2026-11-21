# rutas — Planeación de rutas de distribución

**Estado: PENDIENTE**

**Requisitos que cubrirá:** R15, R16, R17, R18.

**Entradas:**
- Coordenadas del depósito y de los 14 clientes (Sección 7 del enunciado).
- Supuestos del caso: distancia por carretera = 1,3 × distancia euclidiana,
  velocidad media 30 km/h, 8 min de servicio por cliente, duración máxima de
  ruta 150 min.

**Salidas previstas:**
- Formulación matemática del problema (variables, función objetivo, restricciones).
- Tabla comparativa en una instancia reducida (≤ 10 clientes): algoritmo voraz,
  colonia de hormigas y óptimo exacto.
- Tabla del ajuste de hiperparámetros de las hormigas (configuración inicial vs.
  ajustada, ≥ 20 ejecuciones cada una).
- Plan de rutas final para los 14 clientes: secuencia, distancia y duración por ruta,
  número de rutas, distancia total y brecha.
