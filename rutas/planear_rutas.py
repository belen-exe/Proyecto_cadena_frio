"""
R16, R17 y R18 - Planeación de rutas.

  R16: instancia reducida (clientes 1 a 8): hormigas vs voraz vs óptimo exacto (fuerza bruta).
  R17: ajuste de α, β y ρ de las hormigas con el algoritmo de abejas (20 corridas por configuración).
  R18: plan final para los 14 clientes con las hormigas ajustadas.

Genera en rutas/resultados/: resumen_rutas.md y plan_rutas.png.
Uso:  python rutas/planear_rutas.py     (tarda unos 4 minutos, casi todo en R17)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import abejas
import hormigas as aco
import problema as pb

CARPETA_RESULTADOS = Path(__file__).resolve().parent / "resultados"
CLIENTES = list(range(1, 15))
CLIENTES_REDUCIDA = list(range(1, 9))
SEMILLAS_FINALES = list(range(100, 100 + abejas.NUM_CORRIDAS))   # distintas a las de las abejas


def brecha(valor, mejor):
    """Brecha [%] = (valor obtenido − mejor valor conocido) / mejor valor conocido × 100."""
    return 100 * (valor - mejor) / mejor


def km(plan):
    return sum(pb.distancia_ruta(r) for r in plan)


def texto_plan(plan):
    return " ; ".join("0-" + "-".join(map(str, r)) + "-0" for r in plan)


def correr_config(config, semillas):
    """20 corridas del ACO con los 14 clientes. Devuelve la lista de (plan, costo)."""
    return [aco.hormigas(CLIENTES, config["alfa"], config["beta"], config["rho"], semilla=s)
            for s in semillas]


def main():
    CARPETA_RESULTADOS.mkdir(exist_ok=True)

    # ==========================================
    # R16: instancia reducida
    # ==========================================
    print("========== R16: instancia reducida (clientes 1 a 8) ==========")
    optimo = pb.fuerza_bruta(CLIENTES_REDUCIDA)
    plan_voraz8 = pb.voraz(CLIENTES_REDUCIDA)
    corridas8 = [aco.hormigas(CLIENTES_REDUCIDA, **aco.CONFIG_INICIAL, semilla=s)
                 for s in range(abejas.NUM_CORRIDAS)]
    plan_aco8 = min(corridas8, key=lambda x: x[1])[0]
    costos8 = [c for _, c in corridas8]
    c_opt = pb.costo(optimo)

    filas_r16 = [
        ("Óptimo exacto (fuerza bruta)", optimo, c_opt, ""),
        ("Voraz (vecino más cercano)", plan_voraz8, pb.costo(plan_voraz8), ""),
        ("Hormigas, mejor de 20 corridas", plan_aco8, min(costos8), ""),
        ("Hormigas, promedio de 20 corridas", None, float(np.mean(costos8)),
         f"{sum(np.isclose(c, c_opt) for c in costos8)} de 20 corridas llegan al óptimo"),
    ]
    for nombre, plan, c, nota in filas_r16:
        print(f"  {nombre:36s} costo = {c:9.2f}  brecha = {brecha(c, c_opt):5.2f} %  {nota}")

    # ==========================================
    # R17: ajuste con abejas
    # ==========================================
    print("\n========== R17: ajuste de hiperparámetros con abejas (14 clientes) ==========")
    config_ajustada, historia = abejas.abejas(CLIENTES, semilla=0)
    print("  Configuración ajustada:", {k: round(v, 3) for k, v in config_ajustada.items()})

    # Comparación final con 20 semillas NUEVAS (no usadas por las abejas)
    corridas_ini = correr_config(aco.CONFIG_INICIAL, SEMILLAS_FINALES)
    corridas_aju = correr_config(config_ajustada, SEMILLAS_FINALES)
    plan_voraz = pb.voraz(CLIENTES)

    # Mejor solución conocida: la mejor de todo lo calculado aquí
    candidatos = [plan_voraz] + [p for p, _ in corridas_ini + corridas_aju]
    mejor_conocido = min(candidatos, key=pb.costo)
    c_mejor = pb.costo(mejor_conocido)

    filas_r17 = []
    for nombre, config, corridas in [("Inicial (sin ajustar)", aco.CONFIG_INICIAL, corridas_ini),
                                     ("Ajustada (abejas)", config_ajustada, corridas_aju)]:
        costos = np.array([c for _, c in corridas])
        rutas = np.array([len(p) for p, _ in corridas])
        fila = {
            "nombre": nombre, "config": config,
            "media": costos.mean(), "desv": costos.std(ddof=1),
            "fraccion": float(np.mean(np.isclose(costos, c_mejor))),
            "fraccion_2rutas": float(np.mean(rutas == len(mejor_conocido))),
        }
        filas_r17.append(fila)
        print(f"  {nombre:22s} media = {fila['media']:.2f}  desv = {fila['desv']:.2f}  "
              f"alcanzan la mejor = {100 * fila['fraccion']:.0f} %")

    # ==========================================
    # R18: plan final
    # ==========================================
    plan_final = min(corridas_aju, key=lambda x: x[1])[0]
    assert pb.es_factible(plan_final, CLIENTES)
    c_final = pb.costo(plan_final)

    # ¿Se puede con una ruta menos? Cota simple: una sola ruta con TODOS los clientes
    # debe pasar al menos por los clientes 6 y 12 (los más alejados entre sí), así que
    # dura como mínimo  viaje(0→6→12→0) + 14 × 8 min  (desigualdad triangular).
    cota_una_ruta = (pb.T_VIAJE[0, 6] + pb.T_VIAJE[6, 12] + pb.T_VIAJE[12, 0]
                     + pb.SERVICIO_MIN * len(CLIENTES))

    print("\n========== R18: plan final (14 clientes) ==========")
    for i, r in enumerate(plan_final, 1):
        print(f"  Ruta {i}: 0-{'-'.join(map(str, r))}-0   "
              f"{pb.distancia_ruta(r):6.2f} km   {pb.duracion_ruta(r):6.1f} min")
    print(f"  Rutas: {len(plan_final)}   Distancia total: {km(plan_final):.2f} km   "
          f"Brecha: {brecha(c_final, c_mejor):.2f} %")
    print(f"  Una sola ruta duraría al menos {cota_una_ruta:.0f} min > 150 -> "
          f"{len(plan_final)} rutas es el mínimo" if len(plan_final) == 2 else "")

    grafica_plan(plan_final)
    escribir_resumen(optimo, filas_r16, c_opt, config_ajustada, historia, filas_r17,
                     mejor_conocido, c_mejor, plan_voraz, plan_final, cota_una_ruta)
    print("\nGuardado: rutas/resultados/resumen_rutas.md, plan_rutas.png")


def grafica_plan(plan):
    fig, eje = plt.subplots(figsize=(6, 6))
    for i, r in enumerate(plan, 1):
        puntos = pb.COORDENADAS[[0] + r + [0]]
        eje.plot(puntos[:, 0], puntos[:, 1], "o-",
                 label=f"Ruta {i}: {pb.distancia_ruta(r):.1f} km, {pb.duracion_ruta(r):.0f} min")
    for i, (x, y) in enumerate(pb.COORDENADAS):
        eje.annotate("D" if i == 0 else str(i), (x, y), xytext=(4, 4), textcoords="offset points")
    eje.plot(*pb.COORDENADAS[0], "ks", ms=10)
    eje.set_xlabel("x [km]")
    eje.set_ylabel("y [km]")
    eje.set_aspect("equal")
    eje.grid(True, alpha=0.3)
    eje.legend(fontsize=8)
    eje.set_title("Plan de rutas para los 14 clientes (R18)")
    fig.tight_layout()
    fig.savefig(CARPETA_RESULTADOS / "plan_rutas.png", dpi=120)
    plt.close(fig)


def escribir_resumen(optimo, filas_r16, c_opt, config_aju, historia, filas_r17,
                     mejor_conocido, c_mejor, plan_voraz, plan_final, cota_una_ruta):
    r16 = "\n".join(
        f"| {nombre} | {'' if plan is None else len(plan)} | "
        f"{c - pb.M_POR_RUTA * len(optimo) if plan is None else km(plan):.2f} | {c:.2f} | "
        f"{brecha(c, c_opt):.2f} | {'' if plan is None else texto_plan(plan)} {nota} |"
        for nombre, plan, c, nota in filas_r16)
    rangos = ", ".join(f"{k} ∈ [{a}, {b}]" for k, (a, b) in abejas.RANGOS.items())
    r17 = "\n".join(
        f"| {f['nombre']} | {f['config']['alfa']:.2f} | {f['config']['beta']:.2f} | "
        f"{f['config']['rho']:.3f} | {f['media']:.2f} | {f['desv']:.2f} | "
        f"{100 * f['fraccion']:.0f} % | {100 * f['fraccion_2rutas']:.0f} % |"
        for f in filas_r17)
    r18 = "\n".join(
        f"| {i} | 0 → {' → '.join(map(str, r))} → 0 | {len(r)} | "
        f"{pb.distancia_ruta(r):.2f} | {pb.duracion_ruta(r):.1f} |"
        for i, r in enumerate(plan_final, 1))
    mejoro = filas_r17[1]["media"] < filas_r17[0]["media"]
    texto = f"""# Resumen — Planeación de rutas (R15–R18)

Formulación matemática (R15): ver `rutas/formulacion.md`.
Costo de un plan = M·(número de rutas) + distancia total [km], con M = {pb.M_POR_RUTA:.0f}.
Tiempo de una ruta = km / 0,5 km/min + 8 min por cliente ≤ 150 min.

## R16 — Validación frente al óptimo exacto

**Instancia reducida:** depósito + clientes 1 a 8 (mismas coordenadas y reglas que el caso completo).
**Método exacto:** fuerza bruta. Se prueban los 8! = 40 320 órdenes de visita; cada orden se
corta en rutas de la mejor forma posible (programación dinámica sobre los puntos de corte).
Todo plan es algún orden cortado en rutas, así que el mejor de todos es el óptimo.
Hormigas con la configuración inicial (α = {aco.CONFIG_INICIAL['alfa']}, β = {aco.CONFIG_INICIAL['beta']}, ρ = {aco.CONFIG_INICIAL['rho']}),
{aco.NUM_HORMIGAS} hormigas, {aco.NUM_ITERACIONES} iteraciones.

| Método | Rutas | Distancia [km] | Costo | Brecha vs óptimo [%] | Plan |
|---|---|---|---|---|---|
{r16}

## R17 — Ajuste de hiperparámetros con abejas

Hiperparámetros y rangos: {rangos}.
Algoritmo de abejas: {abejas.NUM_EXPLORADORAS} exploradoras, {abejas.NUM_SITIOS} mejores sitios con {abejas.NUM_RECLUTAS} reclutas cada uno,
{abejas.NUM_CICLOS} ciclos, vecindario inicial {100 * abejas.VECINDARIO_INICIAL:.0f} % del rango que se reduce ×{abejas.REDUCCION_VECINDARIO} por ciclo.
Calidad de una configuración = costo promedio de {abejas.NUM_CORRIDAS} corridas independientes del ACO
(semillas 0–{abejas.NUM_CORRIDAS - 1}). Mejor costo medio por ciclo: {', '.join(f'{h:.2f}' for h in historia)}.

Comparación final con {abejas.NUM_CORRIDAS} corridas NUEVAS (semillas {SEMILLAS_FINALES[0]}–{SEMILLAS_FINALES[-1]}, no usadas en el ajuste),
14 clientes. Mejor solución conocida = la mejor encontrada en todas estas corridas y el voraz:
costo {c_mejor:.2f} ({len(mejor_conocido)} rutas, {km(mejor_conocido):.2f} km).

| Configuración | α | β | ρ | Costo medio | Desv. estándar | Alcanzan la mejor conocida | Con {len(mejor_conocido)} rutas |
|---|---|---|---|---|---|---|---|
{r17}

**Conclusión:** el ajuste {'MEJORÓ' if mejoro else 'NO mejoró'} el desempeño de las hormigas
(costo medio {filas_r17[0]['media']:.2f} → {filas_r17[1]['media']:.2f}). Como cada ruta extra suma
M = {pb.M_POR_RUTA:.0f}, el costo medio refleja sobre todo qué fracción de corridas logra el menor número de rutas.

## R18 — Plan de rutas para los 14 clientes

Mejor plan de las {abejas.NUM_CORRIDAS} corridas con la configuración ajustada. Figura: `plan_rutas.png`.

| Ruta | Secuencia | Clientes | Distancia [km] | Duración [min] |
|---|---|---|---|---|
{r18}

- **Número de rutas: {len(plan_final)}.** Distancia total: **{km(plan_final):.2f} km**.
  Brecha respecto de la mejor solución conocida: **{brecha(pb.costo(plan_final), c_mejor):.2f} %**.
- Todas las rutas duran ≤ 150 min y cada cliente aparece exactamente una vez (verificado en el código).
- **¿Podría hacerse con 1 ruta?** No: una ruta con los 14 clientes pasaría por los clientes 6 y 12,
  así que viajaría al menos 0 → 6 → 12 → 0 (desigualdad triangular) y duraría como mínimo
  {cota_una_ruta:.0f} min > 150 min. Por lo tanto {len(plan_final)} rutas es el mínimo posible.
- Como referencia, el voraz necesita {len(plan_voraz)} rutas y {km(plan_voraz):.2f} km.
"""
    (CARPETA_RESULTADOS / "resumen_rutas.md").write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
