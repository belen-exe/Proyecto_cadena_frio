# archivo — Material antiguo (no se usa en los módulos nuevos)

Todo lo que hay aquí es **SIMULADO** y corresponde a versiones anteriores del proyecto.
Se conserva para trazabilidad.

| Archivo | Qué es |
|---|---|
| `datos_sinteticos.py` | Simulador antiguo (24 h, 1 muestra/min, temperatura directa en °C). Reemplazado por `E3_eventos/simulador_E3.py`. |
| `datos_sinteticos_cadena_frio.csv` | Salida de `datos_sinteticos.py`. |
| `datos_modelo_termico.csv` | Salida de la versión anterior de `modelo_termico.py` (commit `7ed239e`; hoy ese script es `E3_eventos/simulador_E3.py`). Lo lee `regresion_matricial_24h.py`. |
| `regresion_matricial_24h.py` | Primer borrador del método 2 de R9 (antes `E2_calentamiento/metodo2_regresion.py`), sobre los datos de 24 h. Reemplazado por `E2_calentamiento/metodo2_regresion.py`. |
| `predicciones_regresion.csv` | Salida de `regresion_matricial_24h.py`. |
