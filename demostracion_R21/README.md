# demostracion_R21 — Demostración en vivo (R21)

**Estado: preparado; falta hacer la demostración y guardar la evidencia aquí.**

R21: durante la sustentación se abre la tapa del contenedor y el sistema debe emitir
la alarma (LED y mensaje serie) frente al jurado. Como todo el montaje es **SIMULADO**
en Wokwi, "abrir la tapa" se representa subiendo la temperatura de los sensores con
sus deslizadores, igual que ocurre en una apertura real: el sensor junto a la tapa
se calienta mucho más que los otros.

Todos los números de este documento (retardos, T², Q) se calcularon con el modelo de
los NTC de Wokwi y el mismo detector que corre en el ESP32.

---

## 1. Cómo funciona el circuito

Cada canal es un **divisor de voltaje** (módulo `wokwi-ntc-temperature-sensor`):

```
3V3 ── R_fijo 10 kΩ ──┬── NTC (10 kΩ a 25 °C, β = 3950) ── GND
                      │
                     OUT ──► GPIO34 / 35 / 32 (ADC de 12 bits, 0–4095)
```

- El NTC **baja su resistencia cuando sube la temperatura**. Como está abajo en el
  divisor, al calentarse baja el voltaje de OUT y **baja la cuenta del ADC**.
  Ejemplo: a 5 °C el NTC vale ≈ 25,9 kΩ y el ADC lee ≈ 2955; a 25 °C lee ≈ 2048.
- El ADC convierte el voltaje en una cuenta: adc = 4095 · R_NTC / (R_fijo + R_NTC).
  De ahí el firmware despeja L = ln(adc / (4095 − adc)) = ln(R_NTC / R_fijo), que es
  la variable que usa la calibración de E1.
- **Pines GPIO34, 35 y 32:** son del ADC1, que funciona aunque se active el Wi-Fi
  (el ADC2 no). GPIO34 y 35 son solo de entrada, ideales para leer sensores.
- **LED de alarma:** GPIO2 → resistor de 220 Ω → LED → GND. La corriente es
  (3,3 V − ≈1,8 V del LED) / 220 Ω ≈ 6,8 mA, segura para el pin (máx. ≈ 40 mA).

### Por qué la prueba de desconexión conecta el pin a 3V3

**En el montaje real**, el resistor fijo va soldado en la placa, junto al ESP32, y el
NTC está en la punta de un cable, dentro de la caja:

```
              PLACA (junto al ESP32)              │  CABLE  │   CAJA
3V3 ── R_fijo 10 kΩ ──┬──────────────────────────┼────╳────┼── NTC ── GND
                      │                          │  corte  │
                      └──► GPIO32
```

Si el cable del sensor se corta (╳), el NTC deja de estar conectado y por R_fijo ya no
circula corriente: **no hay caída de voltaje en R_fijo**, así que el pin queda al mismo
voltaje que 3V3. El ADC lee su valor máximo, **4095**. Con la fórmula del divisor se ve
igual: si R_NTC → ∞ (circuito abierto), adc = 4095 · R_NTC / (R_fijo + R_NTC) → 4095.
Por eso el firmware y el detector de E3 toman una lectura ≥ 4090 como sensor
desconectado (y una ≤ 5 como corto a GND), y por eso en E3 las desconexiones se
simularon con el ADC en 4095.

**En Wokwi**, el módulo `wokwi-ntc-temperature-sensor` trae el R_fijo *por dentro*. El
único cable que se puede quitar es OUT, que está **entre el R_fijo y el ESP32**, y eso
no es lo mismo que cortar el cable del NTC:

| Qué se hace en Wokwi | Qué representa | Qué lee el pin | Resultado |
|---|---|---|---|
| Quitar `["esp:32", "ntc3:OUT", …]` | Pin del ESP32 sin nada conectado ("al aire") | Valores al azar: en una prueba, 1300–2060 cuentas, que parecen 25–43 °C | El firmware no lo reconoce como desconexión; solo el PCA lo nota a los ≈ 11 s, con el mensaje de "tapa abierta" |
| **Cambiarla por `["esp:32", "esp:3V3", …]`** | **Cable del NTC cortado con el R_fijo en la placa** (pin en 3V3, como arriba) | **4095** | `T_3 = NA`, alarma a los **2 s** con `sensor desconectado` |

Conectar el pin a 3V3 reproduce exactamente el voltaje que tendría el pin con el cable
del sensor cortado en el montaje real. Por eso es la forma correcta de simular la
desconexión que pide R11 y que evalúa R13. Quitar OUT simula otra falla (el cable se
suelta del lado del ESP32), que no ocurre si el R_fijo está en la placa.
- **Pines GPIO34, 35 y 32:** son del ADC1, que funciona aunque se active el Wi-Fi
  (el ADC2 no). GPIO34 y 35 son solo de entrada, ideales para leer sensores.
- **LED de alarma:** GPIO2 → resistor de 220 Ω → LED → GND. La corriente es
  (3,3 V − ≈1,8 V del LED) / 220 Ω ≈ 6,8 mA, segura para el pin (máx. ≈ 40 mA).

## 2. Por qué esos rangos y temperaturas

| Valor | De dónde sale |
|---|---|
| **2–8 °C** | Rango de conservación de vacunas (OMS). Es el contexto del proyecto; el límite que importa es 8 °C (R10). |
| **0–40 °C** | Rango de operación pedido en R1: cubre la nevera (≈ 4 °C) y el ambiente (≈ 30 °C). El resistor fijo se diseñó para este rango (`0_diseno/`). |
| **R_fijo = 10 kΩ** | El óptimo para 0–40 °C es √(R_0°C · R_40°C) ≈ 13,4 kΩ; 10 kΩ conserva el 98,3 % de la excursión de voltaje y es el que trae el módulo de Wokwi. Resolución: ≈ 0,02–0,03 °C por cuenta del ADC. |
| **Ts = 1 s** | Justificado en R2 (`1_electronica/resultados/justificacion_Ts.md`): es mucho más rápido que lo que tarda en notarse una apertura (≈ 28 s) y deja 30 muestras en cada apertura de 30 s. |
| **Deslizadores en 5,0 / 5,3 / 4,8 °C** | Es el **estado normal** del detector: con esos valores las temperaturas calibradas quedan en la media de entrenamiento μ ≈ (4,95; 5,10; 4,75) °C. No son iguales porque los coeficientes de E1 son de los sensores simulados (cada uno con su tolerancia y su desfase por posición), mientras que los NTC de Wokwi son ideales. |
| **Umbral Q = 0,178** | Percentil 99,5 de Q en entrenamiento (E3). Q mide cuánto se rompe el patrón "los 3 sensores se mueven juntos". |
| **Umbral T² = 2,55** | Percentil 99,5 de T² en entrenamiento. T² mide cuánto se alejan los 3 sensores **juntos** de la temperatura normal. |

**El detector no compara contra 2–8 °C.** Detecta lo que es distinto de la operación
normal que vio en el entrenamiento. Como en el entrenamiento los tres sensores solo
oscilaron ±0,3 °C alrededor de ≈ 5 °C, basta que los tres suban o bajen juntos
**≈ 0,4 °C** para que T² dé alarma. Es decir, avisa mucho antes de llegar a 8 °C. La
otra cara es que es un detector muy "estricto": si la nevera trabajara normalmente a
otra temperatura, habría que volver a entrenarlo (`E3_eventos/detector.py`).

## 3. Cada cuánto se evalúa el diagnóstico y la alarma

Todo ocurre **una vez por segundo** (cada Ts = 1 s), en este orden:

1. Se leen los 3 canales y se convierten a °C calibrados.
2. Se actualiza el **promedio de los últimos 10 s** de cada canal.
3. Con ese promedio se calculan **T² y Q** y se comparan con los umbrales.
   La muestra es **anómala** si T² o Q superan su umbral, o si algún canal está desconectado.
4. Un contador lleva cuántas muestras anómalas van **seguidas**. La **alarma** se
   enciende cuando llega a **K = 3** y se apaga con la primera muestra normal.
5. Se actualiza el LED y se escribe la fila CSV (y `# ALARMA` o `# Fin de la alarma`
   cuando cambia el estado).

Consecuencias que conviene saber explicar:

- **Al arrancar**, las primeras 10 filas tienen `T2` y `Q` en `NA`: hace falta llenar
  la ventana de 10 s. Lo mismo pasa durante 10 s **después de reconectar** un sensor.
- **Retardo mínimo: 2 s.** Con K = 3 se necesitan las muestras t, t+1 y t+2.
  Es el caso de una desconexión (no pasa por el promedio).
- **Un cambio de temperatura entra poco a poco** en el promedio (cada segundo pesa
  1/10). Un cambio grande supera el umbral enseguida; uno pequeño tarda más.
- **Al quitar el evento**, la alarma tarda unos segundos en apagarse porque el
  promedio todavía contiene valores del evento.
- R13 exige ≤ 60 s en aperturas y ≤ 20 s en desconexiones; todos los casos de abajo
  quedan muy por debajo.

## 4. Cómo leer la salida serie

Cada segundo el ESP32 escribe una fila con 12 columnas separadas por comas:

```
t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,T2,Q,alarma,t_proc_us,Origen
```

| Columna | Unidad | Qué significa | Valor típico en estado normal |
|---|---|---|---|
| `t_ms` | ms | **Marca de tiempo**: milisegundos desde que arrancó el ESP32 (`millis()`). Sube de 1000 en 1000 porque Ts = 1 s; si faltara una fila, se notaría un salto de 2000 (pérdida de muestras, R2). | 549, 1549, 2549, … |
| `adc_1`, `adc_2`, `adc_3` | cuentas (0–4095) | **Lectura cruda** del ADC de 12 bits en GPIO34, 35 y 32. Es el voltaje del divisor convertido en número. Cuanto **más caliente**, **menor** la cuenta (≈ 40 cuentas por °C cerca de 5 °C). **4095** = pin en 3V3 (sensor desconectado). | 2955, 2942, 2963 |
| `T_1`, `T_2`, `T_3` | °C | **Temperatura calibrada** de cada canal con los coeficientes de E1: T = 1/(θ0 + θ1·L) − 273,15. `NA` si el canal es inválido (ADC ≥ 4090 o ≤ 5). | 4,92 / 5,07 / 4,77 |
| `T2` | — (sin unidad) | **Estadístico T² del PCA**: qué tan lejos están los 3 sensores, **juntos**, de la temperatura normal de entrenamiento. Sube si toda la caja se calienta o se enfría. Umbral: **2,55**. `NA` mientras la ventana de 10 s no esté llena (al arrancar, o con un canal inválido). | ≈ 0,01 |
| `Q` | — (sin unidad) | **Estadístico Q del PCA** (error de reconstrucción): cuánto **se rompe el patrón** "los 3 sensores se mueven juntos". Sube si un sensor se separa de los otros, como al abrir la tapa. Umbral: **0,178**. `NA` en los mismos casos que `T2`. | ≈ 0,02 |
| `alarma` | 0 / 1 | **1** si la muestra fue anómala (T² o Q sobre su umbral, o canal inválido) **3 veces seguidas** (K = 3). Es lo que enciende el LED. | 0 |
| `t_proc_us` | µs | **Tiempo de procesamiento** del ciclo (lectura de los 3 ADC + calibración + detector), medido con `micros()`. Se usa en R20. Es el tiempo que reporta Wokwi, no una placa real. | ≈ 390–450 (de 1 000 000 disponibles) |
| `Origen` | — | Siempre `SIMULADO`: marca exigida por el enunciado para todo dato que no sea real. | SIMULADO |

Las líneas que empiezan por `#` no son datos sino mensajes: el de arranque, la memoria
libre (`ESP.getFreeHeap()`, para R20), `# ALARMA en t_ms=…: causa` cuando se enciende la
alarma y `# Fin de la alarma en t_ms=…` cuando se apaga.

### Ejemplos de filas y cómo leerlas

```
549,2955,2942,2963,4.9185,5.0670,4.7651,NA,NA,0,750,SIMULADO
```
**Recién arrancado:** las temperaturas ya salen, pero `T2` y `Q` están en `NA` porque el
promedio de 10 s todavía no tiene 10 muestras. No hay alarma.

```
20549,2955,2942,2963,4.9185,5.0670,4.7651,0.0055,0.0244,0,444,SIMULADO
```
**Estado normal:** `T2` = 0,0055 < 2,55 y `Q` = 0,024 < 0,178. LED apagado.

```
45549,2913,2942,2963,5.9082,5.0670,4.7651,2.1180,13.3642,1,443,SIMULADO
# ALARMA en t_ms=45549: Q sobre el umbral (patron entre sensores roto, p. ej. tapa abierta)
```
**Tapa abierta** (sensor 1 subido a 6,0 °C): `adc_1` bajó de 2955 a 2913 y `T_1` subió
≈ 1 °C mientras los otros dos siguen igual. El patrón se rompe: `Q` = 13,4, unas 75 veces
el umbral. `T2` = 2,1 todavía no pasa su umbral, porque solo un sensor cambió. Alarma
y LED encendidos.

```
5549,2955,2942,4095,4.9185,5.0670,NA,NA,NA,1,389,SIMULADO
# ALARMA en t_ms=2549: sensor desconectado
```
**Sensor 3 desconectado** (pin en 3V3): `adc_3` = 4095, `T_3` = `NA`. Sin los 3 canales
no se puede calcular el PCA, así que `T2` y `Q` también salen en `NA`. La alarma se
enciende por la regla de desconexión, sin pasar por el PCA, a los 2 s del inicio.

(Los valores de `t_ms` y `t_proc_us` de estos ejemplos son ilustrativos; los ADC, las
temperaturas, T² y Q son los que da el firmware con esos deslizadores.)

## 5. Antes de la sustentación

1. Ejecute `python 1_electronica/generar_parametros.py` (copia al firmware la
   calibración de E1 y el detector de E3) y compile el firmware (`pio run` en
   `1_electronica/firmware_esp32/`).
2. Arranque la simulación en Wokwi (sección 5 del README principal). En wokwi.com
   recuerde crear la pestaña `parametros.h`.
3. Compruebe que arranca **sin alarma** con los deslizadores en 5,0 / 5,3 / 4,8 °C
   y espere unos 15 s a que `T2` y `Q` dejen de ser `NA`.

## 6. Ejemplos para probar en la sustentación

Partiendo siempre del estado normal (5,0 / 5,3 / 4,8 °C). "Retardo" es el tiempo desde
que se mueve el deslizador hasta que se enciende el LED; "apagado" es el tiempo desde
que se vuelve al estado normal hasta que se apaga.

### Guion principal (R21)

| Paso | Qué se hace | Qué debe verse |
|---|---|---|
| 1 | Dejar correr 20 s en estado normal | LED apagado, `alarma = 0`, `Q` ≈ 0,02 |
| 2 | **"Abrir la tapa":** subir el sensor 1 a **6,0 °C** | A los **≈ 3 s**: LED encendido y `# ALARMA en t_ms=…: Q sobre el umbral…` |
| 3 | **"Cerrar la tapa":** volver el sensor 1 a 5,0 °C | A los **≈ 8 s**: `# Fin de la alarma`, LED apagado |
| 4 | "Cortar el cable" del sensor 3: en `diagram.json` cambiar `ntc3:OUT` por `esp:3V3` en la línea de `esp:32` (Wokwi reinicia) | Desde el arranque: `adc_3 = 4095`, `T_3 = NA`, alarma a los **2 s** con `sensor desconectado` |
| 5 | Volver a poner `ntc3:OUT` | Arranca normal; `T2`/`Q` en `NA` los primeros 10 s mientras se llena la ventana |

### Más casos (por si el jurado pregunta)

| Caso | Qué se mueve | Q | T² | ¿Alarma? | Retardo | Apagado |
|---|---|---|---|---|---|---|
| Normal | nada | 0,02 | 0,01 | no | — | — |
| Apertura muy leve | sensor 1 → 5,1 °C | 0,10 | 0,01 | **no** (menor que el ruido normal) | — | — |
| Apertura leve | sensor 1 → 5,2 °C | 0,43 | 0,05 | sí, por Q | 8 s | 3 s |
| Apertura media | sensor 1 → 5,5 °C | 3,3 | 0,48 | sí, por Q | 4 s | 7 s |
| Apertura (guion) | sensor 1 → 6,0 °C | 13,4 | 2,1 | sí, por Q | 3 s | 8 s |
| Apertura fuerte | sensor 1 → 7,0 °C | 55 | 9,0 | sí, por Q y T² | 2 s | 9 s |
| Apertura realista | sensor 1 → 6,0 y sensor 2 → 5,6 °C | 10,3 | 3,6 | sí, por Q y T² | 3 s | 8 s |
| Otro sensor | sensor 3 → 6,0 °C | 22,3 | 3,2 | sí | 2 s | 9 s |
| Un sensor se enfría | sensor 1 → 4,0 °C | 14,9 | 2,7 | sí | 2 s | 9 s |
| Toda la caja se calienta poco | los 3 suben 0,3 °C | 0,02 | 1,7 | **no** | — | — |
| Toda la caja se calienta | los 3 suben 0,5 °C | 0,04 | 5,2 | sí, **solo por T²** | 9 s | 2 s |
| Toda la caja se calienta mucho | los 3 suben 1,0 °C | 0,06 | 21 | sí, solo por T² | 5 s | 6 s |
| Toda la caja se enfría | los 3 bajan 0,5 °C | 0,02 | 5,9 | sí, solo por T² | 8 s | 3 s |
| Desconexión breve | pin en 3V3 durante 2 s | — | — | **no** (solo 2 muestras, K = 3) | — | — |
| Desconexión | pin en 3V3 ≥ 3 s | — | — | sí | 2 s | inmediato |
| Pulso de 1 s | sensor 1 → 6,0 °C durante 1 s | 0,11 | 0,01 | **no** (el promedio lo diluye) | — | — |

Qué demuestra cada grupo:

- **Q** reacciona cuando un sensor se separa de los otros (tapa abierta: el sensor
  junto a la tapa se calienta más). Es la parte del detector que aprovecha la
  redundancia entre canales (R12).
- **T²** reacciona cuando los tres se mueven **juntos** fuera de lo normal (toda la
  caja cambia de temperatura): ahí Q no ve nada, porque el patrón no se rompe.
- **El promedio de 10 s y K = 3** evitan falsas alarmas por picos cortos (pulso de 1 s,
  desconexión de 2 s), a cambio de unos segundos de retardo.

Para mover "los 3 juntos", cambie los tres deslizadores lo más rápido posible; si se
mueven uno por uno, durante unos segundos el patrón se rompe y también puede saltar Q.

## 7. Evidencia que debe quedar en esta carpeta

- [ ] `captura_demo.csv`: texto completo del monitor serie durante la demostración.
- [ ] `demo_led_encendido.png`: captura de pantalla de Wokwi con el LED encendido y el mensaje `# ALARMA`.
- [ ] (Opcional) video corto de la demostración.
