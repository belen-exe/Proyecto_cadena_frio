"""
Simulador del Experimento E2 (R8): calentamiento del contenedor.

TODOS LOS DATOS QUE GENERA ESTE SCRIPT SON SIMULADOS (Origen = "SIMULADO").

Procedimiento simulado
----------------------
1. La caja de icopor, con la carga ya preenfriada y los 3 sensores calibrados
   dentro, se deja 150 min (≥ 2 h) en la nevera con la tapa cerrada.
2. Se saca de la nevera (instante `extraccion`) y se deja 60 min (≥ 45 min) a
   temperatura ambiente, sin abrirla.
3. El ESP32 registra los 3 canales cada Ts = 1 s durante todo el experimento.
   La temperatura ambiente (aire de la nevera y luego de la habitación) se
   anota cada 60 s con el termómetro de referencia.

Modelo "real" de la simulación (desconocido para el análisis)
-------------------------------------------------------------
Primer orden (Newton), solución exacta por paso:
    T(t+Ts) = T_amb + (T(t) − T_amb)·exp(−Ts/τ),     τ = C / UA
con C = Σ m·c de la carga y la caja, y UA calculado con las dimensiones, el
espesor de pared y la conductividad del icopor, más un factor de "puentes
térmicos" (bordes y tapa) que el análisis NO conoce.

Archivos generados en E2_calentamiento/datos/
---------------------------------------------
  calentamiento_E2.csv           t_s, adc_1, adc_2, adc_3, Origen   (Ts = 1 s)
  ambiente_E2.csv                t_s, T_amb_ref_C, Origen            (cada 60 s)
  eventos_E2.csv                 evento, t_s, Origen
  descripcion_contenedor.json    material, dimensiones, espesor y masas (R8)
  VERDAD_NO_USAR.json            τ real, temperaturas reales, semillas. NO lo lea el análisis.

Uso:  python E2_calentamiento/simulador_E2.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO))

from comun import modelo_sensor as ms  # noqa: E402

CARPETA_DATOS = Path(__file__).resolve().parent / "datos"
ORIGEN = "SIMULADO"

# ==========================================
# 1. CONFIGURACIÓN DEL EXPERIMENTO
# ==========================================

SEMILLA = 202
TS_S = 1.0
DURACION_NEVERA_MIN = 150     # ≥ 2 h en la nevera
DURACION_AMBIENTE_MIN = 60    # ≥ 45 min a temperatura ambiente
PERIODO_AMBIENTE_S = 60       # cada cuánto se anota la temperatura ambiente
HORA_INICIO_H = 12.5          # la extracción ocurre a las 15:00

TEMP_INICIAL_C = 5.5          # carga preenfriada al meterla en la caja

# Aire de la nevera (igual que en E3)
NEVERA_MEDIA_C = 4.5
NEVERA_AMPLITUD_C = 0.5
NEVERA_PERIODO_MIN = 30.0

# Desfases por posición y ruido de temperatura (los mismos supuestos de E3)
DESVIACIONES = [0.0, 0.15, -0.20]
RUIDO_TEMPERATURA_C = 0.08

# Termómetro de referencia para el ambiente
RESOLUCION_REF_C = 0.1
SIGMA_ERROR_REF_C = 0.05

# ==========================================
# 2. DESCRIPCIÓN DEL CONTENEDOR (lo que el equipo mide y declara en R8)
# ==========================================

CONTENEDOR = {
    "material_pared": "Poliestireno expandido (icopor)",
    "dimensiones_interiores_m": {"largo": 0.22, "ancho": 0.16, "alto": 0.14},
    "espesor_pared_m": 0.025,
    "masa_caja_vacia_kg": 0.15,
    "calor_especifico_caja_J_kgK": 1300.0,
    "carga": "4 botellas de agua de 250 mL (representan la carga + geles)",
    "masa_carga_kg": 1.0,
    "calor_especifico_carga_J_kgK": 4186.0,
    "conductividad_pared_W_mK (tabla)": 0.035,
    "coef_conveccion_W_m2K (supuesto)": 10.0,
    "sensores": "3 NTC calibrados (E1) en el aire interior, entre las botellas",
    "Origen": ORIGEN,
}

# Factor de puentes térmicos (bordes, tapa mal ajustada): solo lo conoce el simulador.
FACTOR_PUENTES_TERMICOS = 1.3


def area_media(espesor):
    """Área de transferencia [m²] evaluada en la superficie media de la pared."""
    d = CONTENEDOR["dimensiones_interiores_m"]
    l, a, h = d["largo"] + espesor, d["ancho"] + espesor, d["alto"] + espesor
    return 2 * (l * a + l * h + a * h)


def tau_real_s():
    c = CONTENEDOR
    capacidad = (c["masa_carga_kg"] * c["calor_especifico_carga_J_kgK"]
                 + c["masa_caja_vacia_kg"] * c["calor_especifico_caja_J_kgK"])
    area = area_media(c["espesor_pared_m"])
    resistencia = (c["espesor_pared_m"] / (c["conductividad_pared_W_mK (tabla)"] * area)
                   + 2 / (c["coef_conveccion_W_m2K (supuesto)"] * area))
    ua = FACTOR_PUENTES_TERMICOS / resistencia
    return capacidad / ua, capacidad, ua


def temperatura_nevera(minuto, fase):
    return NEVERA_MEDIA_C + NEVERA_AMPLITUD_C * np.sin(2 * np.pi * minuto / NEVERA_PERIODO_MIN + fase)


def temperatura_habitacion(minuto_del_dia):
    """Mismo modelo diario de la cocina de E3."""
    return 25 + 3 * np.sin(2 * np.pi * minuto_del_dia / 1440)


def json_legible(objeto):
    texto = json.dumps(objeto, indent=2, ensure_ascii=False)
    return re.sub(r"\[\s*([^\[\]{}\"]*?)\s*\]",
                  lambda m: "[" + " ".join(m.group(1).split()) + "]", texto)


def main():
    rng = np.random.default_rng(SEMILLA)
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    tau_s, capacidad, ua = tau_real_s()
    fase = rng.uniform(0, 2 * np.pi)

    t_extraccion_s = DURACION_NEVERA_MIN * 60
    n = int((DURACION_NEVERA_MIN + DURACION_AMBIENTE_MIN) * 60 / TS_S)
    t_s = np.arange(n) * TS_S

    t_real = np.empty(n)
    t_amb = np.empty(n)
    temperatura = TEMP_INICIAL_C
    factor = np.exp(-TS_S / tau_s)

    for k, t in enumerate(t_s):
        minuto = t / 60
        if t < t_extraccion_s:
            t_amb[k] = temperatura_nevera(minuto, fase)
        else:
            t_amb[k] = temperatura_habitacion(HORA_INICIO_H * 60 + minuto)
        t_real[k] = temperatura
        temperatura = t_amb[k] + (temperatura - t_amb[k]) * factor

    # Lecturas de los sensores -> ADC
    medida = (t_real[:, None] + np.array(DESVIACIONES)[None, :]
              + rng.normal(0, RUIDO_TEMPERATURA_C, size=(n, 3)))
    adc = np.column_stack([ms.temperatura_a_adc(medida[:, i], s, rng=rng)
                           for i, s in enumerate(ms.SENSORES)])

    tabla = pd.DataFrame({"t_s": t_s, "adc_1": adc[:, 0], "adc_2": adc[:, 1],
                          "adc_3": adc[:, 2], "Origen": ORIGEN})
    tabla.to_csv(CARPETA_DATOS / "calentamiento_E2.csv", index=False)

    # Ambiente anotado con el termómetro de referencia cada 60 s
    indices = np.arange(0, n, int(PERIODO_AMBIENTE_S / TS_S))
    lectura = np.round((t_amb[indices] + rng.normal(0, SIGMA_ERROR_REF_C, len(indices)))
                       / RESOLUCION_REF_C) * RESOLUCION_REF_C
    pd.DataFrame({"t_s": t_s[indices], "T_amb_ref_C": np.round(lectura, 1),
                  "Origen": ORIGEN}).to_csv(CARPETA_DATOS / "ambiente_E2.csv", index=False)

    pd.DataFrame({
        "evento": ["inicio_en_nevera", "extraccion", "fin_registro"],
        "t_s": [0, t_extraccion_s, int(t_s[-1])],
        "Origen": ORIGEN,
    }).to_csv(CARPETA_DATOS / "eventos_E2.csv", index=False)

    (CARPETA_DATOS / "descripcion_contenedor.json").write_text(
        json.dumps(CONTENEDOR, indent=2, ensure_ascii=False), encoding="utf-8")

    verdad = {
        "ADVERTENCIA": "Valores reales de la simulación. Ningún análisis debe leer este archivo.",
        "Origen": ORIGEN,
        "semilla": SEMILLA,
        "tau_real_min": tau_s / 60,
        "k_real_1_por_min": 60 / tau_s,
        "capacidad_termica_J_K": capacidad,
        "UA_real_W_K": ua,
        "factor_puentes_termicos": FACTOR_PUENTES_TERMICOS,
        "desviaciones_C": DESVIACIONES,
        "ruido_temperatura_C": RUIDO_TEMPERATURA_C,
        "T_real_C_cada_10s": np.round(t_real[::10], 4).tolist(),
        "T_amb_real_C_cada_10s": np.round(t_amb[::10], 4).tolist(),
    }
    (CARPETA_DATOS / "VERDAD_NO_USAR.json").write_text(json_legible(verdad), encoding="utf-8")

    print(f"Generado: E2_calentamiento/datos/calentamiento_E2.csv ({n} filas, "
          f"{DURACION_NEVERA_MIN} min en nevera + {DURACION_AMBIENTE_MIN} min a ambiente)")
    print("Generado: ambiente_E2.csv, eventos_E2.csv, descripcion_contenedor.json, VERDAD_NO_USAR.json")
    print(f"T real al extraer: {t_real[t_extraccion_s]:.2f} C; al final: {t_real[-1]:.2f} C")


if __name__ == "__main__":
    main()
