# pruebas_simulacion — Salidas del firmware en Wokwi (SIMULADO)

`mediciones_ntc.csv` corresponde al **formato anterior** del firmware
(una fila por sensor y por ciclo):

    Tiempo_ms, Sensor, Temperatura_C, Estado, Origen

Todavía no se ha grabado una corrida con el formato actual
(una fila por ciclo: `t_ms, adc_1, adc_2, adc_3, T_1, T_2, T_3, alarma, Origen`).
Para generarla, siga la sección "Firmware en Wokwi" del README principal y
guarde la salida del monitor serie en esta carpeta.
