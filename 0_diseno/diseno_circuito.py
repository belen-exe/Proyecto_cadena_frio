"""
R1 - Diseño del circuito de acondicionamiento de cada canal.

Circuito de un canal (igual al módulo wokwi-ntc-temperature-sensor):

    3V3 ──[ R_fijo ]──┬──[ NTC ]── GND
                      └──> GPIO (ADC1)

    V(T) = Vcc · R_ntc(T) / (R_fijo + R_ntc(T))
    R_ntc(T) = R0 · exp( β · (1/T_K − 1/T0_K) )

Criterio de selección del resistor fijo
---------------------------------------
Maximizar la EXCURSIÓN de voltaje en el rango de operación 0–40 °C:

    ΔV(R_f) = V(0 °C) − V(40 °C)

Derivando respecto a R_f e igualando a cero:

    dΔV/dR_f = 0   =>   R_f* = sqrt( R_ntc(0 °C) · R_ntc(40 °C) )

Una excursión mayor reparte más cuentas del ADC sobre el rango, es decir,
mejor resolución promedio en °C por cuenta.

Resolución (°C por cuenta del ADC)
----------------------------------
    dV/dT   = Vcc · R_f · (dR/dT) / (R_f + R)²,     dR/dT = −β · R / T_K²
    cuentas/°C = |dV/dT| · 4095 / Vcc
    resolución = 1 / (cuentas/°C)      [°C por cuenta]

Genera en 0_diseno/resultados/:
    memoria_calculo_R1.md, tabla_resolucion.csv,
    curvas_divisor.png, resolucion.png, esquematico.png

Uso:  python 0_diseno/diseno_circuito.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon, Rectangle

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

CARPETA_RESULTADOS = Path(__file__).resolve().parent / "resultados"

# ==========================================
# 1. DATOS DE DISEÑO
# ==========================================

VCC = ms.VCC_V
ADC_MAX = ms.ADC_MAX
R0 = ms.R0_NOMINAL_OHM
BETA = ms.BETA_NOMINAL_K

T_MIN_C = 0.0     # Rango de operación pedido en R1
T_MAX_C = 40.0

# Temperaturas para la tabla de resolución (incluye la zona crítica 2–8 °C).
TEMPERATURAS_TABLA = [0, 2, 5, 8, 20, 30, 40]

# Valores comerciales de la serie E12 entre 1 kΩ y 100 kΩ.
SERIE_E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
VALORES_COMERCIALES = [v * 10 ** e for e in (3, 4) for v in SERIE_E12] + [100e3]

# Valor que impone el simulador: el módulo NTC de Wokwi trae R_fijo = 10 kΩ.
R_FIJO_WOKWI = ms.R_FIJO_NOMINAL_OHM

# Zona lineal aproximada del ADC del ESP32 con atenuación de 11 dB (supuesto de
# hoja de datos): fuera de ~0,15–3,1 V el error del ADC real crece mucho.
V_LINEAL_MIN = 0.15
V_LINEAL_MAX = 3.10

# Autocalentamiento: constante de disipación típica de un NTC de epoxi en aire
# (valor típico de hoja de datos, SUPUESTO; no hay hoja de datos en Wokwi).
CONSTANTE_DISIPACION_MW_POR_C = 1.5

# LED de alarma
R_LED = 220.0
V_LED_ROJO = 1.8      # caída típica de un LED rojo [V] (supuesto)
I_GPIO_MAX_MA = 20.0  # corriente recomendada por pin del ESP32 [mA]

# ==========================================
# 2. FUNCIONES DEL DIVISOR
# ==========================================


def r_ntc(t_c):
    return ms.temperatura_a_resistencia(t_c, R0, BETA)


def voltaje(t_c, r_fijo):
    return ms.resistencia_a_voltaje(r_ntc(t_c), r_fijo, VCC)


def excursion(r_fijo):
    return voltaje(T_MIN_C, r_fijo) - voltaje(T_MAX_C, r_fijo)


def cuentas_por_grado(t_c, r_fijo):
    """Sensibilidad analítica |dADC/dT| [cuentas/°C]."""
    t_k = np.asarray(t_c, dtype=float) + 273.15
    r = r_ntc(t_c)
    dr_dt = -BETA * r / t_k ** 2
    dv_dt = VCC * r_fijo * dr_dt / (r_fijo + r) ** 2
    return np.abs(dv_dt) * ADC_MAX / VCC


def resolucion(t_c, r_fijo):
    """°C equivalentes a una cuenta del ADC."""
    return 1.0 / cuentas_por_grado(t_c, r_fijo)


def resolucion_numerica(t_c, r_fijo, dt=1e-3):
    """Comprobación por diferencias finitas de la resolución analítica."""
    adc_1 = voltaje(t_c, r_fijo) / VCC * ADC_MAX
    adc_2 = voltaje(t_c + dt, r_fijo) / VCC * ADC_MAX
    return dt / np.abs(adc_2 - adc_1)


# ==========================================
# 3. CÁLCULOS
# ==========================================

r_0 = float(r_ntc(T_MIN_C))
r_40 = float(r_ntc(T_MAX_C))
r_optimo = float(np.sqrt(r_0 * r_40))

# Mejor valor comercial E12 (el de mayor excursión)
excursiones = {r: float(excursion(r)) for r in VALORES_COMERCIALES}
r_comercial = max(excursiones, key=excursiones.get)

candidatos = {
    "Óptimo teórico": r_optimo,
    f"E12 más cercano ({r_comercial / 1e3:g} kohm)": r_comercial,
    "Wokwi / adoptado (10 kohm)": R_FIJO_WOKWI,
}

# Tabla comparativa de candidatos
filas_candidatos = []
for nombre, r_f in candidatos.items():
    v0, v40 = float(voltaje(T_MIN_C, r_f)), float(voltaje(T_MAX_C, r_f))
    filas_candidatos.append({
        "Candidato": nombre,
        "R_fijo_ohm": r_f,
        "V_0C_V": v0,
        "V_40C_V": v40,
        "Excursion_V": v0 - v40,
        "Excursion_%_del_optimo": 100 * (v0 - v40) / excursion(r_optimo),
        "Cuentas_0_40C": (v0 - v40) / VCC * ADC_MAX,
        "Resolucion_media_C_por_cuenta": (T_MAX_C - T_MIN_C) / ((v0 - v40) / VCC * ADC_MAX),
    })
tabla_candidatos = pd.DataFrame(filas_candidatos)

# Tabla de resolución (valor adoptado y E12 recomendado)
filas = []
for t in TEMPERATURAS_TABLA:
    filas.append({
        "T_C": t,
        "R_ntc_ohm": float(r_ntc(t)),
        "V_nodo_V_10k": float(voltaje(t, R_FIJO_WOKWI)),
        "ADC_10k": float(voltaje(t, R_FIJO_WOKWI) / VCC * ADC_MAX),
        "Cuentas_por_C_10k": float(cuentas_por_grado(t, R_FIJO_WOKWI)),
        "Resolucion_C_por_cuenta_10k": float(resolucion(t, R_FIJO_WOKWI)),
        "Resolucion_numerica_10k": float(resolucion_numerica(t, R_FIJO_WOKWI)),
        f"Resolucion_C_por_cuenta_{r_comercial / 1e3:g}k": float(resolucion(t, r_comercial)),
        "Origen": "CALCULADO",
    })
tabla_resolucion = pd.DataFrame(filas)

# Comprobaciones adicionales con el valor adoptado (10 kΩ)
v_min = float(voltaje(T_MAX_C, R_FIJO_WOKWI))
v_max = float(voltaje(T_MIN_C, R_FIJO_WOKWI))
adc_min = v_min / VCC * ADC_MAX
adc_max = v_max / VCC * ADC_MAX
en_zona_lineal = V_LINEAL_MIN <= v_min and v_max <= V_LINEAL_MAX

# Potencia máxima en el NTC: ocurre cuando R_ntc = R_fijo -> P = Vcc² / (4·R_fijo)
p_ntc_max_mw = VCC ** 2 / (4 * R_FIJO_WOKWI) * 1e3
autocalentamiento_c = p_ntc_max_mw / CONSTANTE_DISIPACION_MW_POR_C
i_divisor_max_ma = VCC / (R_FIJO_WOKWI + r_40) * 1e3

i_led_ma = (VCC - V_LED_ROJO) / R_LED * 1e3

error_max_analitico = float(
    np.max(np.abs(tabla_resolucion["Resolucion_C_por_cuenta_10k"]
                  - tabla_resolucion["Resolucion_numerica_10k"]))
)

# ==========================================
# 4. GRÁFICAS
# ==========================================

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

t = np.linspace(T_MIN_C, T_MAX_C, 401)

fig, ax = plt.subplots(figsize=(9, 5))
for r_f in [4.7e3, R_FIJO_WOKWI, r_comercial, 22e3, 47e3]:
    estilo = "-" if r_f in (R_FIJO_WOKWI, r_comercial) else ":"
    ax.plot(t, voltaje(t, r_f), estilo, label=f"R_fijo = {r_f / 1e3:g} kΩ (ΔV = {excursion(r_f):.2f} V)")
ax.axvspan(2, 8, color="tab:green", alpha=0.1, label="Zona crítica 2–8 °C")
ax.set_title("Voltaje del divisor vs temperatura (cálculo teórico)")
ax.set_xlabel("Temperatura (°C)")
ax.set_ylabel("V en el nodo (V)")
ax.grid(True)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "curvas_divisor.png", dpi=120)

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(t, resolucion(t, R_FIJO_WOKWI), label="R_fijo = 10 kΩ (adoptado)")
ax.plot(t, resolucion(t, r_comercial), "--", label=f"R_fijo = {r_comercial / 1e3:g} kΩ (E12 óptimo)")
ax.axvspan(2, 8, color="tab:green", alpha=0.1, label="Zona crítica 2–8 °C")
ax.set_title("Resolución: °C equivalentes a 1 cuenta del ADC (12 bits)")
ax.set_xlabel("Temperatura (°C)")
ax.set_ylabel("°C por cuenta")
ax.grid(True)
ax.legend()
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "resolucion.png", dpi=120)


# ---- Esquemático completo (3 canales + LED) ----

def dibujar_resistor(ax, x, y_arriba, y_abajo, texto, ntc=False):
    alto = y_arriba - y_abajo
    margen = alto * 0.2
    ax.plot([x, x], [y_arriba, y_arriba - margen], "k")
    ax.plot([x, x], [y_abajo + margen, y_abajo], "k")
    ax.add_patch(Rectangle((x - 0.18, y_abajo + margen), 0.36, alto - 2 * margen,
                           fill=False, lw=1.5))
    if ntc:  # flecha diagonal del termistor
        ax.annotate("", xy=(x + 0.3, y_arriba - margen * 0.6),
                    xytext=(x - 0.3, y_abajo + margen * 0.6),
                    arrowprops=dict(arrowstyle="-", lw=1))
    ax.text(x + 0.3, (y_arriba + y_abajo) / 2, texto, va="center", fontsize=8)


def dibujar_tierra(ax, x, y):
    for i, ancho in enumerate([0.25, 0.16, 0.07]):
        ax.plot([x - ancho, x + ancho], [y - i * 0.08] * 2, "k")


fig, ax = plt.subplots(figsize=(12, 6))
ax.set_xlim(-1, 12.5)
ax.set_ylim(-0.8, 6.3)
ax.axis("off")

ax.plot([-0.5, 7.5], [5.5, 5.5], "r", lw=1.5)
ax.text(-0.9, 5.5, "3V3", color="r", va="center", fontweight="bold")
ax.plot([-0.5, 11], [0.0, 0.0], "k", lw=1.5)
ax.text(-0.9, 0.0, "GND", va="center", fontweight="bold")

canales = [("ntc1", "GPIO34\n(ADC1_CH6)"), ("ntc2", "GPIO35\n(ADC1_CH7)"),
           ("ntc3", "GPIO32\n(ADC1_CH4)")]
for i, (nombre, pin) in enumerate(canales):
    x = 0.5 + 3 * i
    dibujar_resistor(ax, x, 5.5, 2.9, "R_fijo\n10 kΩ")
    ax.plot(x, 2.9, "ko", ms=5)
    dibujar_resistor(ax, x, 2.9, 0.0, f"NTC {i + 1}\n10 kΩ @25 °C\nβ = 3950", ntc=True)
    ax.plot([x, x + 1.2], [2.9, 2.9], "b")
    ax.text(x + 1.25, 2.9, pin, color="b", va="center", fontsize=8)
    ax.text(x, 6.0, f"Canal {i + 1} ({nombre})", ha="center", fontsize=9)

# LED de alarma: GPIO2 -> 220 Ω -> LED -> GND
x = 10.0
ax.text(x, 6.0, "Alarma", ha="center", fontsize=9)
ax.text(x, 5.0, "GPIO2", color="b", ha="center", fontsize=8)
ax.plot([x, x], [4.8, 4.5], "b")
dibujar_resistor(ax, x, 4.5, 2.6, "220 Ω")
ax.plot([x, x], [2.6, 1.6], "k")
ax.add_patch(Polygon([[x - 0.25, 1.6], [x + 0.25, 1.6], [x, 1.15]], closed=True,
                     fill=False, lw=1.5))
ax.plot([x - 0.25, x + 0.25], [1.15, 1.15], "k", lw=1.5)
ax.text(x + 0.35, 1.4, "LED rojo", fontsize=8, va="center")
ax.plot([x, x], [1.15, 0.0], "k")

ax.set_title("Esquemático del prototipo (ESP32 DevKit + 3 canales NTC + LED) - montaje en Wokwi")
ax.text(5.5, -0.6, "Cada módulo wokwi-ntc-temperature-sensor contiene R_fijo y el NTC; "
        "VCC→3V3, GND→GND, OUT→GPIO.", ha="center", fontsize=8, style="italic")
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "esquematico.png", dpi=120)

# ==========================================
# 5. SALIDAS DE TEXTO
# ==========================================

tabla_resolucion.to_csv(CARPETA_RESULTADOS / "tabla_resolucion.csv", index=False)


def tabla_md(df, formatos):
    encabezado = "| " + " | ".join(df.columns) + " |"
    separador = "|" + "---|" * len(df.columns)
    filas_md = []
    for _, fila in df.iterrows():
        celdas = [formatos.get(c, "{}").format(fila[c]) for c in df.columns]
        filas_md.append("| " + " | ".join(celdas) + " |")
    return "\n".join([encabezado, separador] + filas_md)


cand_md = tabla_md(
    tabla_candidatos.rename(columns={
        "R_fijo_ohm": "R_fijo [Ω]", "V_0C_V": "V(0 °C) [V]", "V_40C_V": "V(40 °C) [V]",
        "Excursion_V": "ΔV [V]", "Excursion_%_del_optimo": "ΔV / ΔV* [%]",
        "Cuentas_0_40C": "Cuentas en 0–40 °C",
        "Resolucion_media_C_por_cuenta": "Resolución media [°C/cuenta]",
    }),
    {"R_fijo [Ω]": "{:.0f}", "V(0 °C) [V]": "{:.3f}", "V(40 °C) [V]": "{:.3f}",
     "ΔV [V]": "{:.3f}", "ΔV / ΔV* [%]": "{:.1f}", "Cuentas en 0–40 °C": "{:.0f}",
     "Resolución media [°C/cuenta]": "{:.4f}"},
)

col_e12 = f"Resolucion_C_por_cuenta_{r_comercial / 1e3:g}k"
res_md = tabla_md(
    tabla_resolucion[["T_C", "R_ntc_ohm", "V_nodo_V_10k", "ADC_10k",
                      "Cuentas_por_C_10k", "Resolucion_C_por_cuenta_10k", col_e12]].rename(columns={
        "T_C": "T [°C]", "R_ntc_ohm": "R_ntc [Ω]", "V_nodo_V_10k": "V nodo [V]",
        "ADC_10k": "ADC [cuentas]", "Cuentas_por_C_10k": "Cuentas/°C",
        "Resolucion_C_por_cuenta_10k": "Resolución 10 kΩ [°C/cuenta]",
        col_e12: f"Resolución {r_comercial / 1e3:g} kΩ [°C/cuenta]",
    }),
    {"T [°C]": "{:.0f}", "R_ntc [Ω]": "{:.0f}", "V nodo [V]": "{:.3f}",
     "ADC [cuentas]": "{:.0f}", "Cuentas/°C": "{:.1f}",
     "Resolución 10 kΩ [°C/cuenta]": "{:.4f}",
     f"Resolución {r_comercial / 1e3:g} kΩ [°C/cuenta]": "{:.4f}"},
)

res_2_8 = resolucion(np.linspace(2, 8, 61), R_FIJO_WOKWI)

memoria = f"""# Memoria de cálculo R1 — Circuito de acondicionamiento

> Generado automáticamente por `0_diseno/diseno_circuito.py`. Valores **CALCULADOS**
> con los parámetros nominales (R0 = {R0:.0f} Ω, β = {BETA:.0f} K, Vcc = {VCC} V, ADC de 12 bits).

## 1. Circuito de cada canal

```
3V3 ──[ R_fijo ]──┬──[ NTC ]── GND
                  └──> GPIO (ADC1)
```

V(T) = Vcc · R_ntc(T) / (R_fijo + R_ntc(T)),  con  R_ntc(T) = R0 · exp(β · (1/T_K − 1/298,15)).

Esquemático completo: `resultados/esquematico.png`.

## 2. Selección del resistor fijo

**Criterio:** maximizar la excursión de voltaje en el rango de operación,
ΔV = V(0 °C) − V(40 °C). Derivando respecto a R_fijo e igualando a cero:

R_fijo* = √( R_ntc(0 °C) · R_ntc(40 °C) ) = √( {r_0:.0f} Ω · {r_40:.0f} Ω ) = **{r_optimo:.0f} Ω**

El valor comercial E12 con mayor excursión es **{r_comercial / 1e3:g} kΩ**.

{cand_md}

**Valor adoptado: 10 kΩ.** El módulo NTC de Wokwi trae el resistor fijo interno de
10 kΩ y no se puede cambiar. Con 10 kΩ se conserva el
{tabla_candidatos.iloc[2]['Excursion_%_del_optimo']:.1f} % de la excursión óptima, así que
la pérdida de resolución frente al óptimo es pequeña. En un montaje físico se usaría
{r_comercial / 1e3:g} kΩ.

## 3. Resolución en °C por cuenta del ADC

Sensibilidad: dV/dT = Vcc · R_fijo · (dR/dT) / (R_fijo + R)², con dR/dT = −β·R/T_K².
Cuentas/°C = |dV/dT| · 4095 / Vcc; resolución = 1 / (cuentas/°C).

{res_md}

- En la zona crítica 2–8 °C, con 10 kΩ, la resolución va de {res_2_8.min():.4f} a
  {res_2_8.max():.4f} °C/cuenta.
- Comprobación por diferencias finitas: diferencia máxima con la fórmula analítica
  = {error_max_analitico:.1e} °C/cuenta.
- La resolución por cuantización es mucho menor que la meta de exactitud de R7
  (0,4 °C entre 0 y 10 °C): el error dominante será el ruido y la calibración, no los bits.

## 4. Comprobaciones del diseño (10 kΩ)

| Comprobación | Valor | Comentario |
|---|---|---|
| Rango de voltaje 0–40 °C | {v_min:.3f} – {v_max:.3f} V | {"dentro" if en_zona_lineal else "FUERA"} de la zona lineal aproximada del ADC del ESP32 ({V_LINEAL_MIN}–{V_LINEAL_MAX} V) |
| Rango de cuentas 0–40 °C | {adc_min:.0f} – {adc_max:.0f} | lejos de 0 y 4095; una lectura ≥ 4090 indica desconexión |
| Corriente máxima del divisor (40 °C) | {i_divisor_max_ma:.3f} mA | despreciable para el regulador de 3V3 |
| Potencia máxima en el NTC (R_ntc = R_fijo) | {p_ntc_max_mw:.3f} mW | P = Vcc² / (4·R_fijo) |
| Autocalentamiento máximo | {autocalentamiento_c:.2f} °C | con constante de disipación {CONSTANTE_DISIPACION_MW_POR_C} mW/°C (típica, supuesta); Wokwi no lo simula. La calibración de E1 absorbe la parte constante |
| Corriente del LED de alarma | {i_led_ma:.1f} mA | (3,3 V − {V_LED_ROJO} V) / 220 Ω, menor que {I_GPIO_MAX_MA:.0f} mA por pin |

Se usan solo pines del ADC1 (GPIO34, 35, 32) porque el ADC2 del ESP32 no se puede
usar cuando el Wi-Fi está activo; así el diseño no depende de esa condición.
"""

(CARPETA_RESULTADOS / "memoria_calculo_R1.md").write_text(memoria, encoding="utf-8")

print(f"R_ntc(0 °C) = {r_0:.0f} ohm, R_ntc(40 °C) = {r_40:.0f} ohm")
print(f"R_fijo óptimo = {r_optimo:.0f} ohm; E12 recomendado = {r_comercial:.0f} ohm; adoptado = 10000 ohm")
print(tabla_candidatos.round(4).to_string(index=False))
print()
print(tabla_resolucion.round(4).to_string(index=False))
print(f"\nGenerado en {CARPETA_RESULTADOS.relative_to(RAIZ_REPO)}: memoria_calculo_R1.md, "
      "tabla_resolucion.csv, curvas_divisor.png, resolucion.png, esquematico.png")
