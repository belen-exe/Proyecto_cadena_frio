"""
R10 - Condiciones de diseño del vehículo, derivadas del modelo de R9 y los datos de R8.

Condiciones: T_amb = 30 °C, T0 = 4 °C, T_lim = 8 °C, ruta máxima 150 min,
factor de seguridad 1,2 sobre el tiempo.

Modelo de R9 con ambiente constante:
    T(t) = T_amb − (T_amb − T0)·e^(−k·t)
    t_lim = (1/k)·ln( (T_amb − T0) / (T_amb − T_lim) )

(i)  k_max: la carga debe tardar al menos FS·t_ruta en llegar a T_lim
         k_max = ln((T_amb − T0)/(T_amb − T_lim)) / (FS·t_ruta)
(ii) factor de mejora = k_prototipo / k_max   (con el k identificado y con el
     extremo superior de su IC 95 %, que es el caso conservador)
(iii) modificación térmica. Del modelo físico k = UA / C:
     - C = Σ m·c de la descripción del contenedor (R8)
     - UA_identificado = k·C            (de R9)
     - UA_teórico = 1 / (L/(λ·A) + 2/(h·A))   (pared plana + convección)
     - f = UA_identificado / UA_teórico  (puentes térmicos: bordes, tapa), obtenido
       de los DATOS; se supone que el rediseño conserva este factor.
     Con f se dimensionan las modificaciones para que k_nuevo ≤ k_max.

Lee:   E2_calentamiento/resultados/parametros_identificados.json,
       E2_calentamiento/datos/descripcion_contenedor.json
Crea:  E2_calentamiento/resultados/resumen_R10.md, diseno_R10.png

Uso:   python E2_calentamiento/diseno_vehiculo.py
"""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

CARPETA = Path(__file__).resolve().parent
CARPETA_RESULTADOS = CARPETA / "resultados"

# Condiciones de diseño de R10
T_AMB = 30.0
T0 = 4.0
T_LIM = 8.0
T_RUTA_MIN = 150.0
FACTOR_SEGURIDAD = 1.2

# Materiales para el rediseño (valores de tabla)
LAMBDA_EPS = 0.035          # W/(m·K) poliestireno expandido
LAMBDA_PU = 0.024           # W/(m·K) espuma rígida de poliuretano
C_AGUA = 4186.0             # J/(kg·K) geles refrigerantes / agua

# ==========================================
# 1. ENTRADAS (R8 y R9)
# ==========================================

param = json.loads((CARPETA_RESULTADOS / "parametros_identificados.json").read_text(encoding="utf-8"))
desc = json.loads((CARPETA / "datos" / "descripcion_contenedor.json").read_text(encoding="utf-8"))

k_proto = param["pso"]["k_1_por_min"]            # 1/min
k_proto_sup = param["pso"]["IC95_k"][1]          # extremo superior IC 95 %

dims = desc["dimensiones_interiores_m"]
L_proto = desc["espesor_pared_m"]
lambda_proto = desc["conductividad_pared_W_mK (tabla)"]
h_conv = desc["coef_conveccion_W_m2K (supuesto)"]
C_proto = (desc["masa_carga_kg"] * desc["calor_especifico_carga_J_kgK"]
           + desc["masa_caja_vacia_kg"] * desc["calor_especifico_caja_J_kgK"])  # J/K


def area_media(espesor):
    l, a, h = (dims["largo"] + espesor, dims["ancho"] + espesor, dims["alto"] + espesor)
    return 2 * (l * a + l * h + a * h)


def ua_teorico(espesor, conductividad):
    area = area_media(espesor)
    return 1.0 / (espesor / (conductividad * area) + 2.0 / (h_conv * area))


def tiempo_hasta_limite(k):
    return math.log((T_AMB - T0) / (T_AMB - T_LIM)) / k


def resolver(funcion, bajo, alto, tol=1e-6):
    """Bisección: raíz de una función creciente o decreciente en [bajo, alto]."""
    f_bajo = funcion(bajo)
    for _ in range(200):
        medio = (bajo + alto) / 2
        if (funcion(medio) > 0) == (f_bajo > 0):
            bajo, f_bajo = medio, funcion(medio)
        else:
            alto = medio
        if alto - bajo < tol:
            break
    return (bajo + alto) / 2


# ==========================================
# 2. (i) RAPIDEZ MÁXIMA ADMISIBLE
# ==========================================

t_requerido = FACTOR_SEGURIDAD * T_RUTA_MIN
cociente = (T_AMB - T0) / (T_AMB - T_LIM)
k_max = math.log(cociente) / t_requerido
tau_min_req = 1 / k_max

# ==========================================
# 3. (ii) FACTOR DE MEJORA
# ==========================================

factor_mejora = k_proto / k_max
factor_mejora_sup = k_proto_sup / k_max
t_lim_proto = tiempo_hasta_limite(k_proto)
t_lim_proto_sup = tiempo_hasta_limite(k_proto_sup)

# ==========================================
# 4. (iii) MODIFICACIÓN TÉRMICA
# ==========================================

ua_ident = k_proto / 60 * C_proto              # W/K   (k en 1/s)
ua_ident_sup = k_proto_sup / 60 * C_proto
ua_teo_proto = ua_teorico(L_proto, lambda_proto)
f_puentes = ua_ident_sup / ua_teo_proto        # conservador: usa el extremo superior


def k_nuevo(espesor, conductividad, masa_extra):
    """k [1/min] de un diseño, con el factor de puentes térmicos identificado."""
    ua = f_puentes * ua_teorico(espesor, conductividad)
    capacidad = C_proto + masa_extra * C_AGUA
    return ua / capacidad * 60


def espesor_solo_aislamiento(conductividad):
    """
    Espesor mínimo que cumple k ≤ k_max sin agregar masa. Al engrosar la pared
    también crece el área, así que k(L) tiene un mínimo: si ni ese mínimo cumple,
    el aislamiento solo es INVIABLE y se devuelve el espesor de ese mínimo.
    """
    malla = np.linspace(0.005, 0.5, 2000)
    k_malla = np.array([k_nuevo(L, conductividad, 0) for L in malla])
    L_mejor = float(malla[np.argmin(k_malla)])
    if k_malla.min() > k_max:
        return L_mejor, False
    return resolver(lambda L: k_nuevo(L, conductividad, 0) - k_max, 0.005, L_mejor), True


opciones = []

# A) Solo más icopor
L_a, viable_a = espesor_solo_aislamiento(LAMBDA_EPS)
opciones.append(("A. Solo pared de icopor más gruesa" + ("" if viable_a else " (mejor posible)"),
                 L_a, LAMBDA_EPS, 0.0))

# B) Cambiar a poliuretano
L_b, viable_b = espesor_solo_aislamiento(LAMBDA_PU)
opciones.append(("B. Solo pared de poliuretano" + ("" if viable_b else " (mejor posible)"),
                 L_b, LAMBDA_PU, 0.0))

# C) Misma caja + masa térmica adicional (geles)
m_c = (f_puentes * ua_teo_proto * 60 / k_max - C_proto) / C_AGUA
opciones.append(("C. Misma caja + geles refrigerantes", L_proto, lambda_proto, m_c))

# D) Recomendada: poliuretano 5 cm + geles hasta cumplir
L_d = 0.05
m_d = max(0.0, (f_puentes * ua_teorico(L_d, LAMBDA_PU) * 60 / k_max - C_proto) / C_AGUA)
m_d = math.ceil(m_d * 10) / 10  # redondeo a 0,1 kg hacia arriba
opciones.append(("D. RECOMENDADA: poliuretano 5 cm + geles", L_d, LAMBDA_PU, m_d))

filas = []
for nombre, L, lam, m in opciones:
    k_n = k_nuevo(L, lam, m)
    filas.append({
        "opcion": nombre, "espesor_cm": 100 * L, "lambda": lam, "masa_extra_kg": m,
        "k_nuevo": k_n, "tau_min": 1 / k_n, "t_hasta_8C_min": tiempo_hasta_limite(k_n),
        "dim_exteriores_cm": "×".join(f"{100 * (v + 2 * L):.0f}" for v in dims.values()),
        "cumple": k_n <= k_max * (1 + 1e-6),
    })

# ==========================================
# 5. SALIDAS
# ==========================================

print(f"(i)   k_max = ln({cociente:.4f}) / ({FACTOR_SEGURIDAD}·{T_RUTA_MIN:.0f} min) = {k_max:.6f} 1/min "
      f"(tau >= {tau_min_req:.0f} min)")
print(f"(ii)  k_prototipo = {k_proto:.6f} (IC sup {k_proto_sup:.6f}) -> factor de mejora "
      f"{factor_mejora:.2f} (conservador {factor_mejora_sup:.2f})")
print(f"      el prototipo llega a 8 C en {t_lim_proto:.0f} min (conservador {t_lim_proto_sup:.0f} min) "
      f"< {t_requerido:.0f} min requeridos")
print(f"(iii) C = {C_proto:.0f} J/K, UA_ident = {ua_ident:.4f} W/K, UA_teorico = {ua_teo_proto:.4f} W/K, "
      f"factor de puentes f = {f_puentes:.3f}")
for f in filas:
    print(f"      {f['opcion']}: espesor {f['espesor_cm']:.1f} cm, masa extra {f['masa_extra_kg']:.2f} kg, "
          f"t(8 C) = {f['t_hasta_8C_min']:.0f} min, {'CUMPLE' if f['cumple'] else 'no cumple'}")

# Gráfica: prototipo vs diseño recomendado
t = np.linspace(0, 300, 601)
fig, ax = plt.subplots(figsize=(9, 5))
for etiqueta, k, estilo in [
    (f"Prototipo (k = {k_proto:.5f} 1/min)", k_proto, "-"),
    ("Prototipo, extremo sup. IC 95 %", k_proto_sup, ":"),
    (f"Diseño recomendado D (k = {filas[-1]['k_nuevo']:.5f} 1/min)", filas[-1]["k_nuevo"], "-"),
]:
    ax.plot(t, T_AMB - (T_AMB - T0) * np.exp(-k * t), estilo, label=etiqueta)
ax.axhline(T_LIM, color="tab:red", ls="--", label="Límite 8 °C")
ax.axvline(T_RUTA_MIN, color="gray", ls="--", label="Ruta máxima 150 min")
ax.axvline(t_requerido, color="k", ls="-.", label="150 min × 1,2 = 180 min")
ax.set_ylim(3, 14)
ax.set_xlabel("Tiempo de ruta (min)")
ax.set_ylabel("Temperatura de la carga (°C)")
ax.set_title("R10 - Calentamiento a 30 °C desde 4 °C (modelo de R9) - SIMULADO")
ax.grid(True, alpha=0.4)
ax.legend(fontsize=8)
fig.tight_layout()
CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
fig.savefig(CARPETA_RESULTADOS / "diseno_R10.png", dpi=120)

tabla = "\n".join(
    f"| {f['opcion']} | {f['espesor_cm']:.1f} | {f['lambda']} | {f['masa_extra_kg']:.2f} | "
    f"{f['dim_exteriores_cm']} | {f['k_nuevo']:.6f} | {f['tau_min']:.0f} | {f['t_hasta_8C_min']:.0f} | "
    f"{'sí' if f['cumple'] else 'no'} |" for f in filas)

resumen = f"""# Resultados R10 — Condiciones de diseño del vehículo

> Generado por `E2_calentamiento/diseno_vehiculo.py` a partir del modelo de R9 y la
> descripción del contenedor de R8. Datos **SIMULADOS**.

Condiciones: T_amb = {T_AMB:.0f} °C, T0 = {T0:.0f} °C, T_lím = {T_LIM:.0f} °C, ruta de
{T_RUTA_MIN:.0f} min, factor de seguridad {FACTOR_SEGURIDAD} sobre el tiempo.

Modelo (R9, ambiente constante): T(t) = T_amb − (T_amb − T0)·e^(−k·t)  ⇒
t_lím = (1/k)·ln[(T_amb − T0)/(T_amb − T_lím)].

## (i) Rapidez de calentamiento máxima admisible

1. Tiempo que debe resistir: t_req = 1,2 × 150 min = **{t_requerido:.0f} min**.
2. Cociente de diferencias: (30 − 4)/(30 − 8) = 26/22 = {cociente:.4f}; ln = {math.log(cociente):.4f}.
3. k_max = {math.log(cociente):.4f} / {t_requerido:.0f} min = **{k_max:.6f} min⁻¹**
   (τ ≥ {tau_min_req:.0f} min = {tau_min_req / 60:.1f} h).

## (ii) Factor de mejora respecto del prototipo

- k del prototipo (R9, PSO): {k_proto:.6f} min⁻¹ (τ = {1 / k_proto:.0f} min);
  extremo superior del IC 95 %: {k_proto_sup:.6f} min⁻¹.
- Con k_proto, la carga llega a 8 °C en {t_lim_proto:.0f} min (caso conservador:
  {t_lim_proto_sup:.0f} min), menos que los {t_requerido:.0f} min exigidos.
- Factor de mejora = k_proto / k_max = {k_proto:.6f} / {k_max:.6f} = **{factor_mejora:.2f}**
  (conservador, con el extremo superior del IC: **{factor_mejora_sup:.2f}**).
  La rapidez de calentamiento debe reducirse ≈ {factor_mejora_sup:.1f} veces.

## (iii) Modificación térmica

Modelo físico: k = UA / C.

1. Capacidad térmica (R8): C = {desc['masa_carga_kg']} kg × {desc['calor_especifico_carga_J_kgK']:.0f} J/(kg·K)
   + {desc['masa_caja_vacia_kg']} kg × {desc['calor_especifico_caja_J_kgK']:.0f} J/(kg·K) = **{C_proto:.0f} J/K**.
2. UA identificado (R9): UA = k·C = ({k_proto:.6f}/60 s⁻¹) × {C_proto:.0f} J/K = **{ua_ident:.4f} W/K**
   (con el extremo superior del IC: {ua_ident_sup:.4f} W/K).
3. UA teórico de pared plana: A_media = {area_media(L_proto):.4f} m²;
   UA = 1/[L/(λ·A) + 2/(h·A)] = 1/[{L_proto}/({lambda_proto}·{area_media(L_proto):.4f}) + 2/({h_conv:.0f}·{area_media(L_proto):.4f})]
   = **{ua_teo_proto:.4f} W/K**.
4. Factor de puentes térmicos (bordes, tapa): f = {ua_ident_sup:.4f}/{ua_teo_proto:.4f} = **{f_puentes:.3f}**.
   Sale de los datos; se supone que el rediseño mantiene la misma calidad de cierre.
5. Condición de diseño: k_nuevo = f·UA_teórico(L, λ) / (C + m_geles·{C_AGUA:.0f}) ≤ k_max.
   El espesor se resuelve por bisección (dimensiones interiores fijas).

| Opción | Espesor [cm] | λ [W/(m·K)] | Geles extra [kg] | Exterior [cm] | k nuevo [min⁻¹] | τ [min] | t hasta 8 °C [min] | Cumple |
|---|---|---|---|---|---|---|---|---|
{tabla}

**Solo con aislamiento {"NO se puede" if not (viable_a or viable_b) else "se puede"} cumplir**
(opciones A y B). Al engrosar la pared de una caja tan pequeña, el área exterior crece casi
tan rápido como la resistencia de la pared, y la convección (2/(h·A)) pone un piso. El
mejor espesor posible deja la carga en {filas[0]['t_hasta_8C_min']:.0f} min (icopor) y
{filas[1]['t_hasta_8C_min']:.0f} min (poliuretano). Con tan poca carga (1 kg), lo que falta es
**capacidad térmica**. (Para paredes gruesas, el modelo de pared plana con área media es solo
aproximado; aun así la tendencia es clara.)

**Recomendación: opción D.** Una caja de poliuretano de 5 cm, con
{filas[-1]['masa_extra_kg']:.1f} kg de geles refrigerantes preenfriados a 4 °C, llega a 8 °C en
{filas[-1]['t_hasta_8C_min']:.0f} min ≥ {t_requerido:.0f} min. La opción C también cumple, pero
necesita {filas[2]['masa_extra_kg']:.1f} kg de geles en la caja actual (más peso y menos espacio para
la carga útil).

Gráfica: `diseno_R10.png`.
"""
(CARPETA_RESULTADOS / "resumen_R10.md").write_text(resumen, encoding="utf-8")
print("Generado: E2_calentamiento/resultados/resumen_R10.md, diseno_R10.png")
