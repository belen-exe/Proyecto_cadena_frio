# demostracion_R21 — Demostración en vivo (R21)

**Estado: preparado; falta hacer la demostración y guardar la evidencia aquí.**

R21: durante la sustentación se abre la tapa del contenedor y el sistema debe emitir
la alarma (LED y mensaje serie) frente al jurado. Como todo el montaje es **SIMULADO**
en Wokwi, "abrir la tapa" se representa subiendo la temperatura de los sensores con
sus deslizadores, igual que ocurre en una apertura real: el sensor junto a la tapa
se calienta mucho más que los otros.

## Antes de la sustentación

1. Ejecute `python 1_electronica/generar_parametros.py` (copia al firmware la
   calibración de E1 y el detector de E3) y compile el firmware (`pio run` en
   `1_electronica/firmware_esp32/`).
2. Arranque la simulación en Wokwi (ver la sección 5 del README principal).
3. Compruebe que arranca **sin alarma**: el `diagram.json` deja los deslizadores en
   el estado normal del detector:

   | Sensor | Deslizador |
   |---|---|
   | 1 (`ntc1`, GPIO34) | 5,0 °C |
   | 2 (`ntc2`, GPIO35) | 5,3 °C |
   | 3 (`ntc3`, GPIO32) | 4,8 °C |

   No son iguales porque los coeficientes de E1 son de los sensores simulados (cada
   uno con su tolerancia), mientras que los NTC de Wokwi son ideales: estos valores
   hacen que las temperaturas calibradas queden en la media de entrenamiento (μ).
   Las primeras 10 filas salen con `T2` y `Q` en `NA` mientras se llena la ventana.

## Guion de la demostración

| Paso | Qué se hace | Qué debe verse |
|---|---|---|
| 1 | Dejar correr 20 s en estado normal | LED apagado, `alarma = 0`, `Q` ≈ 0,02 (umbral 0,178) |
| 2 | **"Abrir la tapa":** subir el sensor 1 a **6,0 °C** (y, si se quiere, el 2 a 5,6 °C) | En ≈ 3–10 s: LED encendido, línea `# ALARMA en t_ms=…: Q sobre el umbral…` |
| 3 | **"Cerrar la tapa":** volver el sensor 1 a 5,0 °C (y el 2 a 5,3 °C) | Tras ≈ 10 s: `# Fin de la alarma`, LED apagado |
| 4 | (Opcional) desconectar el cable OUT de un sensor | ADC = 4095, `T_i = NA`, alarma en ≈ 2–3 s con el mensaje `sensor desconectado` |

El retardo de 3–10 s se debe al promedio móvil de 10 s y a la persistencia K = 3
(R13 pide ≤ 60 s para aperturas y ≤ 20 s para desconexiones).

## Evidencia que debe quedar en esta carpeta

- [ ] `captura_demo.csv`: texto completo del monitor serie durante la demostración.
- [ ] `demo_led_encendido.png`: captura de pantalla de Wokwi con el LED encendido y el mensaje `# ALARMA`.
- [ ] (Opcional) video corto de la demostración.
