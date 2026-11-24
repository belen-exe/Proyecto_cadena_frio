# E2_calentamiento — Experimento E2 y dinámica térmica (R8–R10)

**Estado: Hecho** (datos SIMULADOS). **Requiere haber ejecutado antes E1**, porque
convierte los ADC a °C con `E1_calibracion/resultados/coeficientes_calibracion.json`.

## Cómo ejecutarlo (desde la raíz del repositorio)

```bash
python E2_calentamiento/simulador_E2.py          # 1. R8: datos crudos
python E2_calentamiento/identificacion.py        # 2. R9: PSO + regresión + intervalo al 95 % de k
python E2_calentamiento/diseno_vehiculo.py       # 3. R10: cálculos de diseño
python E2_calentamiento/comparar_con_verdad.py   # 4. (opcional) verificación final
python E2_calentamiento/pso.py                   # (opcional) autoprueba del PSO con Rosenbrock
```

## Archivos

| Archivo | Qué es |
|---|---|
| `simulador_E2.py` | Caja con la carga en la nevera 150 min y luego 60 min a temperatura ambiente; registro continuo a Ts = 1 s |
| `pso.py` | PSO de implementación propia (inercia decreciente 0,9 → 0,4; c1 = c2 = 2) |
| `metodo2_regresion.py` | Segundo método: regresión lineal de la ecuación discreta exacta (promedios de 1 min) |
| `identificacion.py` | R9: ajusta k y T0 con el PSO (5 semillas), contrasta con la regresión, que da el intervalo al 95 % de k |
| `diseno_vehiculo.py` | R10: k máximo admisible, factor de mejora y modificación térmica |
| `comparar_con_verdad.py` | Único script que lee `VERDAD_NO_USAR.json`; solo verifica al final |
| `datos/calentamiento_E2.csv` | `t_s, adc_1, adc_2, adc_3, Origen` |
| `datos/ambiente_E2.csv` | Temperatura ambiente anotada con el termómetro de referencia cada 60 s |
| `datos/eventos_E2.csv` | Instantes de inicio, extracción y fin |
| `datos/descripcion_contenedor.json` | Material, dimensiones, espesor de pared y masas (R8) |
| `resultados/parametros_identificados.json` | k y τ de ambos métodos, T0 y el intervalo al 95 % de k. Lo lee `diseno_vehiculo.py` |
| `resultados/resumen_R9.md`, `resumen_R10.md` | Memorias de cálculo con todos los números |
| `resultados/*.png` | Registro completo, datos vs modelo, residuos, convergencia del PSO y diseño de R10 |

## Modelo

dT/dt = k·(T_amb − T), con la solución exacta por paso
T[n+1] = T_amb + (T[n] − T_amb)·e^(−k·Δt). Aquí **k** es la rapidez de calentamiento
y τ = 1/k.

## Qué revisar para saber que funciona

- `identificacion.py`: las 5 semillas del PSO dan el mismo k; la diferencia con la
  regresión es de pocas décimas de % y el k del PSO cae dentro del intervalo al 95 %.
- `diseno_vehiculo.py`: (i) k_max ≈ 0,00093 min⁻¹; (ii) factor de mejora ≈ 4,9 (≈ 5,1 conservador);
  (iii) la opción recomendada imprime `CUMPLE` (t hasta 8 °C ≥ 180 min).
- `comparar_con_verdad.py`: error de k < 1 % en ambos métodos y el intervalo al 95 %
  contiene el k real.
