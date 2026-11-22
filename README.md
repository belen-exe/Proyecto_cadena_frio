# Monitor inteligente de cadena de frío con ESP32

Proyecto final de **Sistemas Inteligentes**: monitor de temperatura multicanal con
ESP32 para un contenedor aislado de vacunas (rango permitido 2–8 °C), con
calibración de los sensores, modelo de calentamiento del contenedor, detección de
anomalías (apertura de tapa y desconexión de un sensor) y planeación de las rutas
de distribución a 14 clientes.

> **TODO EL PROYECTO ES SIMULADO**
> - el circuito y el firmware del ESP32 corren en el simulador **Wokwi**;
> - los datos "experimentales" (E1, E2, E3) se generan con scripts de **Python**.
>
> Todo dato generado lleva la columna `Origen = SIMULADO`, y las gráficas dicen
> "SIMULADO" en el título.

### Conceptos mínimos

- **Termistor NTC**: resistencia que baja cuando sube la temperatura.
- **Divisor de voltaje**: el NTC va en serie con un resistor fijo; el voltaje en el
  punto medio depende de la temperatura.
- **ADC**: convierte ese voltaje en un número entero ("cuenta") entre 0 y 4095
  (12 bits). En este circuito, **más temperatura → cuenta más baja**.
- **Sensor desconectado**: el punto medio queda pegado a 3,3 V y el ADC marca ≈ 4095.

---

## 1. Estructura del repositorio

```
Proyecto_cadena_frio/
├── README.md                 Este archivo
├── requirements.txt          Librerías de Python (numpy, pandas, matplotlib)
├── comun/                    Modelo del sensor simulado (T → R → V → ADC), usado por todos los simuladores
├── 0_diseno/                 Diseño del circuito, resistor fijo, resolución y esquemático (R1)
├── 1_electronica/            Justificación de Ts y verificación de pérdida de muestras (R2), montaje (R3)
│   ├── firmware_esp32/       Proyecto PlatformIO + Wokwi del ESP32
│   └── pruebas_simulacion/   Capturas del monitor serie del firmware
├── E1_calibracion/           Experimento E1 y calibración ADC → °C (R4–R7) — PENDIENTE
├── E2_calentamiento/         Experimento E2 y modelo térmico con PSO (R8–R10) — PENDIENTE (hay un borrador)
├── E3_eventos/               Experimento E3: datos normales y eventos (R11) y, más adelante, el detector (R12–R14)
├── rutas/                    Planeación de rutas (R15–R18) — PENDIENTE
└── archivo/                  Simuladores y CSV antiguos, solo para trazabilidad
```

| Carpeta | Requisitos | Estado |
|---|---|---|
| `comun/` | Soporte de R4, R8, R11 (modelo del sensor simulado) | Hecho |
| `0_diseno/` | R1 | Hecho |
| `1_electronica/` | R2, R3 | Parcial (faltan la captura de 10 min y la captura de pantalla de Wokwi) |
| `1_electronica/` | R19, R20, R21 | PENDIENTE (necesitan la calibración de E1 y el detector) |
| `E1_calibracion/` | R4, R5, R6, R7 | PENDIENTE |
| `E2_calentamiento/` | R8, R9, R10 | PENDIENTE (borrador del segundo método de R9) |
| `E3_eventos/` | R11 (datos y tabla de eventos) | Hecho (simulado) |
| `E3_eventos/` | R12, R13, R14 (detector) | PENDIENTE |
| `rutas/` | R15, R16, R17, R18 | PENDIENTE |
| Todo el repositorio | R22 (informe y reproducibilidad) | Parcial |

Detalle de lo "Parcial" en `1_electronica/`: el firmware ya lee los 3 canales con
Ts = 1000 ms y emite CSV, y Ts está justificado numéricamente. Falta que el equipo
grabe la captura de 10 minutos en Wokwi (y la verifique con `verificar_perdida.py`)
y tome la captura de pantalla del montaje. Ver `1_electronica/README.md`.

## 2. Flujo de datos entre carpetas

```
comun/modelo_sensor.py         (sensores simulados: T → ADC)
        │
        ▼
E1_calibracion   ──► coeficientes de calibración ADC → °C por canal
        │
        ├──────────────► E2_calentamiento  (datos ADC → °C → modelo térmico, PSO)
        │
        └──────────────► E3_eventos        (datos ADC → °C → detector de anomalías)
                                 │
                                 ▼
                     parámetros del detector
                                 │
                                 ▼
               1_electronica/firmware_esp32  (calibración + detector en el ESP32)
```

Hoy existe solo el primer eslabón (`comun/`) y los datos de E3. Mientras no exista
la calibración de E1, el análisis de E3 usa la conversión β nominal, marcada como
**"conversión provisional, sin calibrar"**. `rutas/` es independiente de los demás.

## 3. Instalación

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
```

## 4. Cómo ejecutar los scripts existentes

Todos los scripts calculan sus rutas a partir de su propia ubicación, así que se
pueden lanzar desde cualquier carpeta. Se recomienda ejecutarlos desde la raíz del
repositorio, en este orden:

| # | Comando (desde la raíz) | Qué hace | Archivos que genera |
|---|---|---|---|
| 1 | `python comun/modelo_sensor.py` | (Opcional) Imprime los parámetros de los 3 sensores simulados y la cuenta ADC en algunas temperaturas | Ninguno |
| 2 | `python E3_eventos/simulador_E3.py` | Simula las tres sesiones de E3 | `E3_eventos/datos/entrenamiento.csv`, `validacion.csv`, `prueba.csv`, `tabla_eventos.csv`, `VERDAD_NO_USAR.json` |
| 3 | `python E3_eventos/exploratorio.py` | Estadísticas y gráficas de E3 (ADC y °C provisional, con los eventos sombreados) | `E3_eventos/resultados/exploratorio_entrenamiento.png`, `exploratorio_validacion.png`, `exploratorio_prueba.png`, `exploratorio_histograma.png` |
| 4 | `python 0_diseno/diseno_circuito.py` | Cálculo del resistor fijo, resolución y esquemático (R1) | `0_diseno/resultados/memoria_calculo_R1.md`, `tabla_resolucion.csv`, `curvas_divisor.png`, `resolucion.png`, `esquematico.png` |
| 5 | `python 1_electronica/justificacion_ts.py` | Justificación numérica de Ts (R2); usa los datos de E3 | `1_electronica/resultados/justificacion_Ts.md` |
| 6 | `python 1_electronica/verificar_perdida.py [captura.csv]` | Pérdida de muestras de una captura del firmware (R2); necesita la captura de Wokwi | `1_electronica/resultados/perdida_muestras.md` |
| 7 | `python E2_calentamiento/metodo2_regresion.py` | Borrador del segundo método de R9 sobre los datos de 24 h del simulador **anterior** | `archivo/predicciones_regresion.csv` |

Los simuladores usan semillas fijas: al volver a ejecutarlos se obtienen
exactamente los mismos archivos. Los scripts que abren gráficas esperan a que se
cierren las ventanas; para ejecutarlos sin ventanas use la variable de entorno
`MPLBACKEND=Agg`.

`archivo/datos_sinteticos.py` es el simulador antiguo; no hace falta ejecutarlo
(escribe `datos_sinteticos_cadena_frio.csv` en la carpeta desde donde se lance).

## 5. Firmware en Wokwi

### Circuito y tabla de pines

Cada canal es un módulo `wokwi-ntc-temperature-sensor`, que ya incluye el NTC
(10 kΩ a 25 °C, β = 3950) y un resistor fijo interno de 10 kΩ:
`3V3 ── R_fijo 10 kΩ ── OUT ── NTC ── GND`.

| Elemento | Pin del elemento | Pin del ESP32 |
|---|---|---|
| Sensor 1 (`ntc1`) | VCC / GND / OUT | 3V3 / GND / **GPIO34** |
| Sensor 2 (`ntc2`) | VCC / GND / OUT | 3V3 / GND / **GPIO35** |
| Sensor 3 (`ntc3`) | VCC / GND / OUT | 3V3 / GND / **GPIO32** |
| Resistor 220 Ω (`r1`) | terminal 1 / terminal 2 | **GPIO2** / ánodo del LED |
| LED rojo (`led1`) | ánodo / cátodo | resistor 220 Ω / GND |

GPIO34, 35 y 32 pertenecen al ADC1 del ESP32. El circuito completo está en
`1_electronica/firmware_esp32/diagram.json`; el esquemático en
`0_diseno/resultados/esquematico.png`, y la lista de materiales y los pasos para
reproducir el montaje en `1_electronica/README.md`.

### Opción A: VS Code + PlatformIO + extensión Wokwi

1. Instale en VS Code las extensiones **PlatformIO IDE** y **Wokwi Simulator**
   (Wokwi pide activar una licencia gratuita la primera vez: `F1 → Wokwi: Request a New License`).
2. Abra la carpeta `1_electronica/firmware_esp32/` como proyecto.
3. Compile: botón ✓ de PlatformIO (o `pio run` en una terminal). Esto crea
   `.pio/build/esp32dev/firmware.bin`, que es lo que lee `wokwi.toml`.
4. `F1 → Wokwi: Start Simulator`. Se abre el circuito y, debajo, el monitor serie.
5. Haga clic sobre un sensor NTC para cambiar su temperatura con el deslizador.

### Opción B: wokwi.com (navegador)

1. En <https://wokwi.com> cree un proyecto nuevo **ESP32 (Arduino)**.
2. Copie el contenido de `src/main.cpp` en `sketch.ino` y el de `diagram.json`
   en la pestaña `diagram.json`.
3. Pulse ▶ (Start). El monitor serie aparece debajo del circuito.

### Cómo leer el monitor serie

La primera línea, que empieza por `#`, es informativa. Luego viene el encabezado y
una fila por segundo:

```
# Sistema de cadena de frio iniciado (SIMULADO)
t_ms,adc_1,adc_2,adc_3,T_1,T_2,T_3,alarma,Origen
```

El LED (GPIO2) se enciende cuando `alarma = 1`. Para guardar una corrida, copie
el texto del monitor serie a un `.csv` dentro de `1_electronica/pruebas_simulacion/`.
La conversión a °C del firmware es **provisional** (β nominal) hasta que exista la
calibración de E1.

## 6. Diccionario de datos

### `E3_eventos/datos/entrenamiento.csv`, `validacion.csv`, `prueba.csv`

Una fila por instante de muestreo (Ts = 1 s). Solo contienen lo que vería el
sistema real: no hay temperaturas ni estados.

| Columna | Unidad | Significado |
|---|---|---|
| `t_s` | s | Tiempo desde el inicio de la sesión |
| `adc_1`, `adc_2`, `adc_3` | cuentas (0–4095) | Lectura cruda del ADC de 12 bits de cada sensor. ≈ 4095 = sensor desconectado |
| `Origen` | — | Siempre `SIMULADO` |

Sesiones: entrenamiento = 30 min de operación normal; validación = 20 min de
operación normal (independiente); prueba = 70 min con 4 aperturas de 30 s y 2
desconexiones de 60 s.

### `E3_eventos/datos/tabla_eventos.csv`

Instante real de inicio y fin de cada evento de la sesión de prueba.

| Columna | Unidad | Significado |
|---|---|---|
| `tipo` | — | `apertura` (tapa abierta) o `desconexion` (un sensor desconectado) |
| `sensor` | — | Número del sensor desconectado (1–3); vacío en las aperturas |
| `t_inicio_s` | s | Inicio del evento, en la escala `t_s` de `prueba.csv` |
| `t_fin_s` | s | Fin del evento (primer instante en que ya no está activo) |
| `Origen` | — | Siempre `SIMULADO` |

### Salida serie del firmware (formato actual)

| Columna | Unidad | Significado |
|---|---|---|
| `t_ms` | ms | Instante de la lectura desde el arranque del ESP32 (`millis()`) |
| `adc_1`, `adc_2`, `adc_3` | cuentas (0–4095) | Lectura cruda de GPIO34, GPIO35 y GPIO32 |
| `T_1`, `T_2`, `T_3` | °C | Temperatura con la conversión β provisional; `NA` si la lectura es inválida (ADC ≤ 5 o ≥ 4090, o fuera de 0–40 °C) |
| `alarma` | 0 / 1 | 1 si algún canal está fuera de 2–8 °C o es inválido |
| `Origen` | — | Siempre `SIMULADO` |

### `1_electronica/pruebas_simulacion/mediciones_ntc.csv` (formato ANTERIOR)

Corrida de Wokwi con el firmware viejo, una fila por sensor y por ciclo. Aún no
hay una corrida grabada con el formato actual.

| Columna | Unidad | Significado |
|---|---|---|
| `Tiempo_ms` | ms | Instante de la lectura desde el arranque |
| `Sensor` | — | Número del sensor (1–3) |
| `Temperatura_C` | °C | Temperatura con la conversión β nominal |
| `Estado` | — | `NORMAL`, `ALARMA` (fuera de 2–8 °C) o `ERROR` |
| `Origen` | — | `SIMULADO` |

### `archivo/` (CSV antiguos, una fila por sensor y por minuto)

| Columna | Unidad | Significado |
|---|---|---|
| `FechaHora` | fecha-hora | Marca de tiempo simulada (desde 2026-01-01 00:00) |
| `Tiempo_min` | min | Minutos desde el inicio |
| `Sensor` | — | Número del sensor (1–3) |
| `Temperatura_C` | °C | Temperatura simulada directamente (sin pasar por ADC); vacía si el sensor está desconectado |
| `Temperatura_ambiente_C` | °C | Ambiente simulado (solo en `datos_modelo_termico.csv` y `predicciones_regresion.csv`) |
| `Tapa_abierta` | bool / 0-1 | Tapa abierta en ese minuto |
| `Estado_sensor` | — | `OK` o `DESCONECTADO` |
| `Estado` | — | `NORMAL`, `ALARMA` o `ERROR` |
| `Origen` | — | `SINTETICO` o `SINTETICO_MODELO_TERMICO` (equivalen a SIMULADO) |

`predicciones_regresion.csv` agrega además las variables de la regresión
(`Temperatura_anterior`, `Sensor_2`, `Sensor_3`, `Temperatura_anterior_x_tapa`,
`Ambiente_x_tapa`, en °C o 0/1) y `Temperatura_real`, `Temperatura_predicha` y
`Error` (°C).

## 7. Regla de los datos "verdaderos": `VERDAD_NO_USAR.json`

Como los datos son simulados, el simulador conoce la verdad: las constantes de
tiempo, las temperaturas reales en cada instante, los parámetros exactos de cada
sensor y las semillas. Todo eso se guarda en `E3_eventos/datos/VERDAD_NO_USAR.json`.

**Ningún análisis puede leer ese archivo.** En un experimento real esa información
no existiría: el sistema solo ve cuentas del ADC y la tabla de eventos anotada
durante el experimento. Si un ajuste, un umbral o una elección de componentes usara
la verdad, los resultados quedarían inflados y no serían defendibles. El archivo
solo sirve para que el equipo verifique, al final, que el simulador hizo lo que se
esperaba.

## 8. Limitaciones de la simulación

- **Sensores ideales en Wokwi**: el módulo NTC de Wokwi sigue exactamente la
  ecuación β, sin tolerancias, sin autocalentamiento y sin retardo térmico. Su
  temperatura se fija a mano con un deslizador, así que las series de tiempo de
  E1–E3 se generan en Python, no en Wokwi.
- **Resistor fijo interno de 10 kΩ**: en Wokwi el resistor del divisor viene dentro
  del módulo y no se puede cambiar. El cálculo de R1 da como óptimo ≈ 13,4 kΩ
  (12 kΩ en la serie E12); se adoptó 10 kΩ, que conserva el 98,3 % de la excursión
  de voltaje óptima.
- **ADC ideal**: Wokwi y `comun/modelo_sensor.py` usan un ADC lineal. El ADC real
  del ESP32 no es lineal cerca de los extremos y es más ruidoso.
- **El ruido es un supuesto**: 0,08 °C de ruido de temperatura y 2 cuentas de ruido
  del ADC no salen de mediciones; tampoco las tolerancias de ±1 % de R0, β y R_fijo.
- **Modelo térmico simplificado**: primer orden (Newton) con τ supuestas
  (cerrada 2000 min, abierta 28,07 min) y un supuesto nuevo, `TAU_RECUPERACION =
  2 min`, para que el aire junto al sensor vuelva a la temperatura del contenido
  tras cerrar la tapa. El contenido no se calienta durante una apertura de 30 s,
  y la respuesta distinta de cada sensor es un factor supuesto (1,0; 0,6; 0,35).
- **Nevera y cocina supuestas**: nevera 4,5 ± 0,5 °C con periodo de 30 min; cocina
  25 + 3·sen(2π·minuto/1440) °C.
