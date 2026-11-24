# Justificación numérica de Ts (R2)

> Generado por `1_electronica/justificacion_ts.py` con los datos **SIMULADOS** de E3.
> Temperaturas con la conversión β nominal (**provisional, sin calibrar**).

## (a) Dinámicas observadas en los datos

**Ruido en operación normal** (entrenamiento, 30 min):

| Canal | σ [cuentas] | σ [°C] |
|---|---|---|
| adc_1 | 4.06 | 0.096 |
| adc_2 | 3.94 | 0.093 |
| adc_3 | 3.94 | 0.094 |

**Rapidez de calentamiento durante las aperturas** (pendiente por mínimos cuadrados
dentro de cada apertura de 30 s, en °C/min):

| Inicio [s] | adc_1 | adc_2 | adc_3 |
|---|---|---|---|
| 600 | 0.750 | 0.399 | 0.199 |
| 1800 | 0.634 | 0.430 | 0.165 |
| 2400 | 0.642 | 0.392 | 0.320 |
| 3600 | 0.445 | 0.192 | 0.174 |

- Pendiente media del canal más expuesto: **0.618 °C/min** (0.0103 °C/s, canal adc_1).
- Con Ts = 1 s la temperatura cambia 0.0103 °C por muestra,
  0.11 veces el ruido: una muestra sola no basta y el detector
  debe acumular varias. El cambio alcanza 3σ de ruido tras **28 s**, dentro de
  los 60 s permitidos. Muestrear más rápido no acelera esto: lo fija la física.
- **Desconexión:** el ADC salta a la saturación en un solo paso (muestras intermedias por
  evento: [0, 0]). Es un escalón: su retardo de detección depende solo de Ts.

## (b) Cotas superiores desde R13

El detector confirma una anomalía con K = 3 muestras consecutivas
(para rechazar picos aislados).

| Condición | Cálculo | Ts máximo |
|---|---|---|
| Desconexión detectada en ≤ 20 s | K·Ts ≤ 20 s → Ts ≤ 20/3 | 6.67 s |
| ≥ 10 muestras dentro de una apertura de 30 s | Ts ≤ 30/10 | 3.00 s |
| **Cota superior** | mínimo de las dos | **3.00 s** |

## (c) Cota inferior

| Tarea por ciclo | Tiempo |
|---|---|
| Enviar una línea de 50 bytes a 115200 baudios | 4.34 ms |
| Leer 3 canales del ADC (cota holgada) | 0.30 ms |
| **Cota inferior** (factor de seguridad 2) | **9.3 ms** |

## Decisión

Intervalo admisible: 9.3 ms ≤ Ts ≤ 3.00 s. **Ts = 1 s**
(cumple), porque:

- retardo de peor caso ante una desconexión = 3 s, con margen
  6.7× frente a 20 s;
- da 30 muestras por apertura, suficientes para promediar ruido;
- ocupa el 0.46 % del ciclo en transmisión y lectura, y genera
  3600 filas/h (≈ 176 KB/h), un volumen fácil de manejar;
- un Ts menor no mejora la detección de aperturas (la limita la rapidez física de
  calentamiento) y solo multiplica los datos.
