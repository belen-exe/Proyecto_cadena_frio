# E3_eventos — Datos de operación y detector de anomalías (R11–R14)

**Estado: Hecho** (datos SIMULADOS). **Requiere haber ejecutado antes E1**, porque
el detector convierte los ADC a °C con `E1_calibracion/resultados/coeficientes_calibracion.json`.

## Cómo ejecutarlo (desde la raíz del repositorio)

```bash
python E3_eventos/simulador_E3.py     # 1. R11: datos crudos de las tres sesiones y tabla de eventos
python E3_eventos/exploratorio.py     # 2. (opcional) estadísticas y gráficas de los datos crudos
python E3_eventos/detector.py         # 3. R12 y R14: PCA y umbrales, SOLO con entrenamiento.csv
python E3_eventos/evaluacion.py       # 4. R13: aplica el detector a validación y prueba, sin reajustar
```

El paso 4 necesita el 3, y el 3 necesita el 1 y la calibración de E1.

## Archivos

| Archivo | Qué es |
|---|---|
| `simulador_E3.py` | Genera las tres sesiones: caja en la nevera, aperturas de tapa de 30 s y desconexiones de un sensor |
| `exploratorio.py` | Describe los datos crudos (ADC y °C provisional) con los eventos sombreados. No fija ningún parámetro |
| `detector.py` | R12: suavizado, PCA a mano, elección de k, T², Q, umbrales y persistencia. R14: compresión. **Solo lee `entrenamiento.csv`** |
| `evaluacion.py` | R13: falsas alarmas por hora en validación y retardo de cada evento en prueba. Carga el JSON del detector; no recalcula nada |
| `datos/entrenamiento.csv` | 30 min de operación normal: `t_s, adc_1, adc_2, adc_3, Origen` (Ts = 1 s) |
| `datos/validacion.csv` | 20 min de operación normal, independientes del entrenamiento |
| `datos/prueba.csv` | 70 min con 4 aperturas de 30 s y 2 desconexiones |
| `datos/tabla_eventos.csv` | `tipo, sensor, t_inicio_s, t_fin_s, Origen`: instante real de inicio y fin de cada evento de prueba |
| `datos/VERDAD_NO_USAR.json` | Temperaturas reales de la simulación. **Ningún análisis lo lee** |
| `resultados/parametros_detector.json` | μ, s, autovectores P, autovalores λ, k, umbrales, K y el archivo del que salieron |
| `resultados/resumen_E3.md` | Formulación, demostración de R12, tablas de R13, desviaciones y R14 |
| `resultados/codo_pca.png` | Gráfica de codo de los autovalores (R12) |
| `resultados/deteccion_prueba.png` | T², Q, umbrales y alarma en la sesión de prueba, con los eventos sombreados (R13) |
| `resultados/exploratorio_*.png` | Gráficas de los datos crudos de cada sesión |

## Cómo funciona el detector (en palabras)

1. Cada lectura ADC se pasa a °C con la calibración de E1 y se promedian los últimos 10 s.
2. En operación normal los 3 sensores suben y bajan juntos (la oscilación de la nevera
   les llega a todos). El PCA encuentra esa dirección común: con **k = 1** componente
   se conserva el 98,8 % de la variación.
3. Para cada muestra se calculan dos números:
   - **T²**: qué tan lejos está la muestra dentro del patrón normal;
   - **Q**: cuánto de la muestra no encaja en el patrón (por ejemplo, una apertura
     calienta mucho al sensor 1 y poco al 3).
4. Si T² o Q superan su umbral (percentil 99,5 de entrenamiento), o un ADC llega a
   ≥ 4090 (sensor desconectado), la muestra es anómala. La alarma suena si hay
   **3 muestras anómalas seguidas**.

## Qué revisar para saber que funciona

- `detector.py`: imprime la tabla de autovalores con k = 1, los dos umbrales y los
  tres números de R14 (información conservada ≈ 98,8 %, compresión 3, Q medio ≈ 0,036).
- `evaluacion.py`:
  - la tabla "¿de qué sesión salen los parámetros?" tiene diferencia **0** solo en
    entrenamiento (demostración de R12);
  - validación: 0 falsas alarmas por hora → `CUMPLE`;
  - prueba: los 6 eventos detectados, aperturas en 21–28 s (meta ≤ 60 s) y
    desconexiones en ≤ 2 s (meta ≤ 20 s).

## Limitación conocida

En la sesión de prueba hay unas 32 falsas alarmas por hora. No es una meta de R13
(que solo exige ≤ 1/h en validación), pero se reporta y se explica en la sección
"Desviaciones" de `resultados/resumen_E3.md`: el entrenamiento (30 min) contiene un
solo ciclo de la nevera y el sensor 1 tarda unos 2 min en recuperarse tras cada
apertura. No se reajustó nada mirando validación ni prueba.
