"""
VERIFICACIÓN FINAL de E2 contra la verdad de la simulación.

Este es el ÚNICO script de E2 que lee VERDAD_NO_USAR.json. No forma parte del
análisis: solo comprueba, después de identificar, que k y los intervalos al 95 %
contienen el valor real con que se generaron los datos.

Uso:  python E2_calentamiento/comparar_con_verdad.py
"""

import json
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
verdad = json.loads((CARPETA / "datos" / "VERDAD_NO_USAR.json").read_text(encoding="utf-8"))
param = json.loads((CARPETA / "resultados" / "parametros_identificados.json").read_text(encoding="utf-8"))

k_real = verdad["k_real_1_por_min"]
print("Comparación con la VERDAD de la simulación (solo verificación)\n")
print(f"k real = {k_real:.6f} 1/min (tau = {verdad['tau_real_min']:.1f} min, "
      f"UA real = {verdad['UA_real_W_K']:.4f} W/K, puentes térmicos = {verdad['factor_puentes_termicos']})")

for metodo in ("pso", "regresion"):
    r = param[metodo]
    error = 100 * (r["k_1_por_min"] - k_real) / k_real
    ic = r["IC95_k"]
    ic_est = r["IC95_k_solo_estadistico"]
    print(f"\n{metodo.upper():10s} k = {r['k_1_por_min']:.6f}  error = {error:+.2f} %")
    print(f"  IC95 total        [{ic[0]:.6f}, {ic[1]:.6f}] -> "
          f"{'contiene' if ic[0] <= k_real <= ic[1] else 'NO contiene'} el valor real")
    print(f"  IC95 solo ruido   [{ic_est[0]:.6f}, {ic_est[1]:.6f}] -> "
          f"{'contiene' if ic_est[0] <= k_real <= ic_est[1] else 'NO contiene'} el valor real")
