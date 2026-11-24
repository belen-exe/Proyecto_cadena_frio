"""
R1 - Diseño del circuito de acondicionamiento (versión simple).

Entregables que genera en 0_diseno/resultados/:
  1. esquematico.png         Diagrama del circuito (3 canales NTC + LED de alarma)
  2. memoria_calculo_R1.md   Memoria de cálculo del resistor fijo + tabla de resolución
  3. tabla_resolucion.csv    Resolución en °C por cuenta del ADC

Circuito de cada canal:   3V3 ──[ R_fijo ]──┬──[ NTC ]── GND
                                            └──> GPIO (ADC)

Uso:  python 0_diseno/diseno_circuito.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon, Rectangle

CARPETA_RESULTADOS = Path(__file__).resolve().parent / "resultados"

# ==========================================
# 1. DATOS DE DISEÑO
# ==========================================

VCC = 3.3          # V, alimentación del divisor (pin 3V3)
ADC_MAX = 4095     # ADC de 12 bits
R0 = 10_000.0      # Ω, resistencia del NTC a 25 °C
BETA = 3950.0      # K, coeficiente β del NTC
T0_K = 298.15      # K (25 °C)

T_MIN, T_MAX = 0.0, 40.0               # rango de operación pedido en R1
TEMPERATURAS_TABLA = [0, 5, 20, 40]    # ≥ 3 temperaturas del rango
R_ADOPTADO = 10_000.0                  # resistor del módulo NTC de Wokwi
CANDIDATOS_E12 = [8_200.0, 10_000.0, 12_000.0, 15_000.0, 18_000.0]


def r_ntc(t_c):
    """Ecuación β: resistencia del NTC [Ω] a t_c [°C]."""
    return R0 * np.exp(BETA * (1 / (t_c + 273.15) - 1 / T0_K))


def voltaje(t_c, r_fijo):
    """Voltaje del nodo del divisor [V]."""
    r = r_ntc(t_c)
    return VCC * r / (r_fijo + r)


def resolucion(t_c, r_fijo):
    """°C equivalentes a 1 cuenta del ADC = 1 / |dADC/dT|."""
    r = r_ntc(t_c)
    dr_dt = -BETA * r / (t_c + 273.15) ** 2            # Ω/°C
    dv_dt = VCC * r_fijo * dr_dt / (r_fijo + r) ** 2    # V/°C
    cuentas_por_grado = abs(dv_dt) * ADC_MAX / VCC
    return 1 / cuentas_por_grado


# ==========================================
# 2. RESISTOR FIJO
# ==========================================
# Criterio: máxima variación de voltaje en 0–40 °C, ΔV = V(0 °C) − V(40 °C).
# Derivando ΔV respecto a R_fijo e igualando a 0:  R_fijo* = √(R(0 °C)·R(40 °C)).

r_0, r_40 = r_ntc(T_MIN), r_ntc(T_MAX)
r_optimo = np.sqrt(r_0 * r_40)
dv_optimo = voltaje(T_MIN, r_optimo) - voltaje(T_MAX, r_optimo)

candidatos = pd.DataFrame({"R_fijo_ohm": CANDIDATOS_E12})
candidatos["V_0C"] = voltaje(T_MIN, candidatos["R_fijo_ohm"])
candidatos["V_40C"] = voltaje(T_MAX, candidatos["R_fijo_ohm"])
candidatos["dV"] = candidatos["V_0C"] - candidatos["V_40C"]
candidatos["pct_optimo"] = 100 * candidatos["dV"] / dv_optimo
mejor_e12 = candidatos.loc[candidatos["dV"].idxmax(), "R_fijo_ohm"]
pct_adoptado = float(candidatos.loc[candidatos["R_fijo_ohm"] == R_ADOPTADO, "pct_optimo"].iloc[0])

# ==========================================
# 3. TABLA DE RESOLUCIÓN (R_fijo adoptado = 10 kΩ)
# ==========================================

tabla = pd.DataFrame({"T_C": TEMPERATURAS_TABLA})
tabla["R_ntc_ohm"] = r_ntc(tabla["T_C"])
tabla["V_nodo_V"] = voltaje(tabla["T_C"], R_ADOPTADO)
tabla["ADC_cuentas"] = tabla["V_nodo_V"] / VCC * ADC_MAX
tabla["Resolucion_C_por_cuenta"] = resolucion(tabla["T_C"], R_ADOPTADO)
tabla["Origen"] = "CALCULADO"

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
tabla.round(4).to_csv(CARPETA_RESULTADOS / "tabla_resolucion.csv", index=False)

# ==========================================
# 4. DIAGRAMA DEL CIRCUITO
# ==========================================


def resistor(ax, x, y_arriba, y_abajo, texto, ntc=False):
    m = 0.2 * (y_arriba - y_abajo)
    ax.plot([x, x], [y_arriba, y_arriba - m], "k")
    ax.plot([x, x], [y_abajo + m, y_abajo], "k")
    ax.add_patch(Rectangle((x - 0.18, y_abajo + m), 0.36, y_arriba - y_abajo - 2 * m, fill=False, lw=1.5))
    if ntc:  # línea diagonal = resistencia variable con la temperatura
        ax.plot([x - 0.3, x + 0.3], [y_abajo + 0.6 * m, y_arriba - 0.6 * m], "k", lw=1)
    ax.text(x + 0.3, (y_arriba + y_abajo) / 2, texto, va="center", fontsize=8)


fig, ax = plt.subplots(figsize=(12, 6))
ax.set_xlim(-1, 12)
ax.set_ylim(-0.8, 6.3)
ax.axis("off")
ax.plot([-0.5, 7.5], [5.5, 5.5], "r", lw=1.5)
ax.text(-0.9, 5.5, "3V3", color="r", va="center", fontweight="bold")
ax.plot([-0.5, 11], [0, 0], "k", lw=1.5)
ax.text(-0.9, 0, "GND", va="center", fontweight="bold")

for i, pin in enumerate(["GPIO34", "GPIO35", "GPIO32"]):
    x = 0.5 + 3 * i
    ax.text(x, 6.0, f"Canal {i + 1}", ha="center", fontsize=9)
    resistor(ax, x, 5.5, 2.9, "R_fijo\n10 kΩ")
    ax.plot(x, 2.9, "ko", ms=5)
    resistor(ax, x, 2.9, 0.0, f"NTC {i + 1}\n10 kΩ @25 °C\nβ = 3950", ntc=True)
    ax.plot([x, x + 1.2], [2.9, 2.9], "b")
    ax.text(x + 1.25, 2.9, pin, color="b", va="center", fontsize=8)

x = 10.0  # LED de alarma: GPIO2 → 220 Ω → LED → GND
ax.text(x, 6.0, "Alarma", ha="center", fontsize=9)
ax.text(x, 5.0, "GPIO2", color="b", ha="center", fontsize=8)
ax.plot([x, x], [4.8, 4.5], "b")
resistor(ax, x, 4.5, 2.6, "220 Ω")
ax.plot([x, x], [2.6, 1.6], "k")
ax.add_patch(Polygon([[x - 0.25, 1.6], [x + 0.25, 1.6], [x, 1.15]], closed=True, fill=False, lw=1.5))
ax.plot([x - 0.25, x + 0.25], [1.15, 1.15], "k", lw=1.5)
ax.text(x + 0.35, 1.4, "LED rojo", fontsize=8, va="center")
ax.plot([x, x], [1.15, 0], "k")

ax.set_title("Diagrama del circuito: ESP32 + 3 canales NTC (divisor de voltaje) + LED de alarma")
fig.tight_layout()
fig.savefig(CARPETA_RESULTADOS / "esquematico.png", dpi=120)

# ==========================================
# 5. MEMORIA DE CÁLCULO
# ==========================================

filas_candidatos = "\n".join(
    f"| {r / 1e3:g} kΩ | {v0:.3f} | {v40:.3f} | {dv:.3f} | {p:.1f} % |"
    for r, v0, v40, dv, p in candidatos[["R_fijo_ohm", "V_0C", "V_40C", "dV", "pct_optimo"]].itertuples(index=False)
)
filas_tabla = "\n".join(
    f"| {t:.0f} | {r:.0f} | {v:.3f} | {a:.0f} | **{res:.4f}** |"
    for t, r, v, a, res in tabla[["T_C", "R_ntc_ohm", "V_nodo_V", "ADC_cuentas",
                                  "Resolucion_C_por_cuenta"]].itertuples(index=False)
)

memoria = f"""# Memoria de cálculo R1 — Circuito de acondicionamiento

> Generado por `0_diseno/diseno_circuito.py`. Valores calculados con los datos nominales.

## 1. Diagrama del circuito

![Diagrama](esquematico.png)

Cada canal es un divisor de voltaje: `3V3 ── R_fijo ── nodo ── NTC ── GND`, y el nodo
va a un pin del ADC del ESP32 (GPIO34, GPIO35, GPIO32). El LED de alarma va en GPIO2
con un resistor de 220 Ω.

## 2. Datos

| Dato | Valor |
|---|---|
| NTC | R0 = 10 kΩ a 25 °C, β = 3950 K |
| Alimentación | Vcc = 3,3 V |
| ADC | 12 bits (0–4095 cuentas) |
| Rango de operación | 0 a 40 °C |

Ecuaciones:

- NTC: R(T) = R0 · e^(β·(1/T − 1/298,15)), con T en kelvin.
- Divisor: V = Vcc · R(T) / (R_fijo + R(T)).
- ADC: cuenta = V / Vcc · 4095.

## 3. Cálculo del resistor fijo

**Criterio:** elegir el R_fijo que dé la mayor variación de voltaje entre 0 y 40 °C,
ΔV = V(0 °C) − V(40 °C). Más variación significa más cuentas del ADC para el mismo
rango, es decir, mejor resolución.

**Paso 1.** Resistencia del NTC en los extremos del rango:
R(0 °C) = {r_0:.0f} Ω y R(40 °C) = {r_40:.0f} Ω.

**Paso 2.** Al derivar ΔV respecto a R_fijo e igualar a cero se obtiene:

R_fijo* = √(R(0 °C) · R(40 °C)) = √({r_0:.0f} · {r_40:.0f}) = **{r_optimo:.0f} Ω**

**Paso 3.** Comparación de valores comerciales (ΔV óptimo = {dv_optimo:.3f} V):

| R_fijo | V(0 °C) [V] | V(40 °C) [V] | ΔV [V] | % del óptimo |
|---|---|---|---|---|
{filas_candidatos}

**Decisión: R_fijo = 10 kΩ.** El mejor valor comercial sería {mejor_e12 / 1e3:g} kΩ, pero el
módulo NTC de Wokwi trae 10 kΩ fijo. Con 10 kΩ se obtiene el {pct_adoptado:.1f} % de la
variación óptima, una pérdida despreciable.

## 4. Resolución en °C por cuenta del ADC (R_fijo = 10 kΩ)

Resolución = 1 / |dADC/dT|, con

dADC/dT = 4095 · R_fijo · (dR/dT) / (R_fijo + R)²  y  dR/dT = −β · R / T²  (T en kelvin).

| T [°C] | R_NTC [Ω] | V nodo [V] | ADC [cuentas] | Resolución [°C/cuenta] |
|---|---|---|---|---|
{filas_tabla}

En todo el rango, una cuenta del ADC equivale a unos 0,02–0,03 °C, mucho menos que la
exactitud pedida en R7 (0,4 °C). La resolución no limita la medición.
"""
(CARPETA_RESULTADOS / "memoria_calculo_R1.md").write_text(memoria, encoding="utf-8")

print(f"R(0 C) = {r_0:.0f} ohm, R(40 C) = {r_40:.0f} ohm -> R_fijo optimo = {r_optimo:.0f} ohm")
print(f"Adoptado 10 kohm: {pct_adoptado:.1f} % de la variacion optima")
print(tabla.drop(columns="Origen").round(4).to_string(index=False))
print("Generado en 0_diseno/resultados: esquematico.png, memoria_calculo_R1.md, tabla_resolucion.csv")
