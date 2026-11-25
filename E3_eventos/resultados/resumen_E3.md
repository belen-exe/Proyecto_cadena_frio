# Resumen E3 — Detector de anomalías con PCA (R12–R14)

Todos los datos son **SIMULADOS**. Los parámetros del detector se fijaron solo con
`entrenamiento.csv` (`detector.py`); validación y prueba solo se evaluaron
(`evaluacion.py`), sin reajustar nada.

## R12 — Detector

### Formulación matemática

Cada muestra n da un vector de 3 temperaturas calibradas (E1) y suavizadas con un
promedio móvil de V = 10 muestras:

    x[n] = (1/V) · Σ_(j=0..V−1) T[n−j]          (vector de 3 elementos, °C)

**Entrenamiento** (N = 1791 muestras de `entrenamiento.csv`):

    μ = (1/N) Σ x[n]                    media de cada sensor
    s = desviación estándar de cada sensor
    z[n] = (x[n] − μ) / s               (elemento a elemento)
    R = ZᵀZ / (N − 1)                   matriz 3 × 3 (Z: las N filas z[n])
    R·pᵢ = λᵢ·pᵢ                        autovalores λ₁ ≥ λ₂ ≥ λ₃ y autovectores pᵢ
    P = [p₁ … p_k]                      las k componentes retenidas (3 × k)

**Estadísticos de una muestra nueva** (z con μ y s de entrenamiento):

    t = Pᵀ·z                            coordenadas de z en las componentes retenidas
    T² = Σ_(i=1..k) tᵢ² / λᵢ            distancia DENTRO del patrón normal
    Q  = ‖z − P·Pᵀ·z‖²                  lo que el patrón normal NO explica

**Regla de decisión**:

    anómala[n] = (T²[n] > umbral_T²) o (Q[n] > umbral_Q) o (algún ADC ≥ 4090)
    alarma[n]  = anómala[n] y anómala[n−1] y … y anómala[n−K+1]      (K = 3)

**Criterio para k**: el menor k con Σ_(i≤k) λᵢ / Σλᵢ ≥ 0,90.

**Criterio para los umbrales**: percentil 99.5 de T² y de Q en entrenamiento
(se acepta que el 0.5 % de las muestras normales lo supere; la
persistencia K filtra los picos aislados).

### Parámetros

| Parámetro | Valor | Cómo se fijó |
|---|---|---|
| Suavizado | promedio móvil causal de 10 s | a priori: baja el ruido ≈ 3 veces y es 3 veces más corto que una apertura |
| Componentes k | 1 | varianza acumulada >= 0.9 (fijado a priori) |
| Umbral T² | 2.5488 | percentil 99.5 en entrenamiento |
| Umbral Q | 0.1781 | percentil 99.5 en entrenamiento |
| Persistencia K | 3 muestras | a priori |
| Desconexión | ADC ≥ 4090 → muestra anómala directamente | regla física, sin PCA |

Autovalores de la matriz de correlación (gráfica de codo en `codo_pca.png`):

| componente | λ | varianza [%] |
|---|---|---|
| 1 | 2.9643 | 98.81 |
| 2 | 0.0193 | 0.64 |
| 3 | 0.0163 | 0.54 |

### Demostración de que solo se usó entrenamiento

1. `detector.py` lee un único archivo de datos: `E3_eventos/datos/entrenamiento.csv`
   (queda registrado en `parametros_detector.json`, campo `archivos_leidos`), con
   N = 1791 muestras, t = 9–1799 s.
2. `evaluacion.py` no calcula ningún parámetro: solo carga el JSON y lo aplica.
3. Comprobación numérica: se recalculan μ, s y los umbrales con cada sesión por separado.
   Solo entrenamiento reproduce los valores del JSON (diferencia ≈ 0, error de redondeo);
   con validación o prueba saldrían valores distintos.

| sesión | dif. máx. μ [°C] | dif. máx. s [°C] | dif. umbral T² | dif. umbral Q |
|---|---|---|---|---|
| entrenamiento | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0e+00 |
| validacion | 1.5e-02 | 1.2e-02 | 3.3e-01 | 2.8e-03 |
| prueba | 5.6e-02 | 2.0e-02 | 9.3e-01 | 4.7e-01 |

## R13 — Desempeño

**Validación** (20 min de operación normal): 0 alarma(s) →
**0.00 falsas alarmas/h** (meta ≤ 1/h) → **CUMPLE**.

**Prueba**:

| evento | sensor | intervalo [s] | detectado | retardo [s] | meta | cumple | alarma ya encendida |
|---|---|---|---|---|---|---|---|
| apertura |  | 600–630 | sí | 26 | ≤ 60 | sí | no |
| desconexion | 3 | 1200–1260 | sí | 2 | ≤ 20 | sí | no |
| apertura |  | 1800–1830 | sí | 21 | ≤ 60 | sí | no |
| apertura |  | 2400–2430 | sí | 26 | ≤ 60 | sí | no |
| desconexion | 1 | 3000–3060 | sí | 0 | ≤ 20 | sí | sí |
| apertura |  | 3600–3630 | sí | 28 | ≤ 60 | sí | no |

Detectados: **100 %**. Falsas alarmas en prueba: 37 (31.71/h).
Metas de R13 (falsas alarmas en validación, 100 % detectados y retardos):
**CUMPLEN**. Gráfica: `deteccion_prueba.png`.

## Desviaciones (se reportan, NO se corrigieron mirando validación ni prueba)

En la sesión de prueba hubo **37 falsas alarmas (31.7/h)**, aunque en
validación hubo 0. Diagnóstico de cada una: 14 por T² y
23 por Q (16 de estas en los 4 min siguientes al fin de un evento).

- **Por T²**: con k = 1, T² mide solo la oscilación común de la nevera, que es comportamiento
  normal. El umbral (percentil 99.5) quedó justo en la cresta de esa oscilación
  porque el entrenamiento (30 min) contiene un único ciclo de 30 min; la prueba dura 70 min y
  cualquier cresta un poco más alta lo supera. El entrenamiento es demasiado corto para
  representar toda la variación normal.
- **Por Q tras un evento**: después de cerrar la tapa, el aire junto al sensor 1 vuelve a la
  temperatura del contenido con τ ≈ 2 min. Pasado el margen de 60 s de la Sección 8 todavía
  queda una diferencia entre sensores que rompe el patrón, y Q la ve. Físicamente el sistema
  aún no ha vuelto a la normalidad, pero la definición la cuenta como falsa alarma.
- **Por Q en el resto (7)**: un percentil 99.5 deja, por definición,
  un 0.5 % de muestras normales por encima. Como el promedio móvil hace que
  las muestras vecinas se parezcan, esas superaciones vienen en grupos y la persistencia
  K = 3 no alcanza a filtrarlas.
- **Retardos de 0 s no son reales**: en desconexion (t = 3000 s) la alarma ya estaba encendida por una falsa alarma cuando empezó el evento. Sin ella, una desconexión se detecta en K − 1 = 2 s (primera lectura en 4095 + K muestras seguidas).

Posibles mejoras (habría que justificarlas con entrenamiento o con criterios físicos, no
ajustándolas a la prueba): entrenar con una sesión normal más larga (varios ciclos de la nevera),
usar un umbral con margen sobre el máximo de entrenamiento, o no evaluar T² cuando k = 1
y solo representa la oscilación común.

## R14 — Compresión

| Medida | Fórmula | Valor | Interpretación |
|---|---|---|---|
| (i) Información conservada | Σλ(1..k) / Σλ | 0.9881 | con 1 de 3 componentes se conserva el 98.8 % de la variación |
| (ii) Factor de compresión | 3 / k | 3.00 | cada muestra se guarda con 1 número(s) en vez de 3 |
| (iii) Error de reconstrucción | promedio de Q = promedio de ‖z − P·Pᵀ·z‖² | 0.0357 | de una varianza total de 3 (en z) se pierde ≈ 1.2 % |
