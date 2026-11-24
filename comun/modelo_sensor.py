"""
Modelo del canal de medición: termistor NTC -> divisor de voltaje -> ADC del ESP32.

TODO LO QUE GENERA ESTE MÓDULO ES SIMULADO.

Circuito de cada canal (igual al módulo wokwi-ntc-temperature-sensor):

    3V3 ──[ R_fijo ]──┬──[ NTC ]── GND
                      │
                    nodo ──> pin ADC del ESP32

    V_nodo = Vcc · R_ntc / (R_fijo + R_ntc)
    cuenta = round( V_nodo / Vcc · 4095 )      (ADC ideal de 12 bits)

Como el NTC baja su resistencia cuando sube la temperatura, la cuenta ADC
BAJA cuando la temperatura SUBE. Si el NTC se desconecta (circuito abierto),
el nodo queda conectado a 3V3 a través de R_fijo y el ADC marca ≈ 4095.

Ecuación β del termistor:

    R_ntc(T) = R0 · exp( β · (1/T_K − 1/T0_K) ),   T_K = T_°C + 273.15

Todos los simuladores del proyecto deben importar ESTE módulo para que
los "sensores físicos" sean los mismos en E1, E2 y E3.
"""

from dataclasses import dataclass, asdict

import numpy as np

# ==========================================
# 1. PARÁMETROS NOMINALES (hoja de datos / módulo de Wokwi)
# ==========================================

# Voltaje de alimentación del divisor [V] (pin 3V3 del ESP32).
VCC_V = 3.3

# Resolución del ADC: 12 bits -> cuentas enteras de 0 a 4095.
ADC_BITS = 12
ADC_MAX = 2 ** ADC_BITS - 1  # 4095

# Resistencia nominal del NTC a la temperatura de referencia T0 [Ω].
R0_NOMINAL_OHM = 10_000.0

# Coeficiente β nominal del NTC [K]. Es el mismo valor que usa diagram.json.
BETA_NOMINAL_K = 3950.0

# Temperatura de referencia de R0 [K] (25 °C).
T0_K = 298.15

# Resistor fijo del divisor [Ω]. El módulo de Wokwi trae uno interno de 10 kΩ.
R_FIJO_NOMINAL_OHM = 10_000.0

# ==========================================
# 2. DISPERSIÓN ENTRE SENSORES (supuestos de la simulación)
# ==========================================

# Tolerancias relativas de fabricación. Cada sensor recibe un valor fijo,
# sorteado de forma uniforme en [nominal·(1 − tol), nominal·(1 + tol)].
TOLERANCIA_R0 = 0.01      # ±1 % en R0
TOLERANCIA_BETA = 0.01    # ±1 % en β
TOLERANCIA_R_FIJO = 0.01  # ±1 % en R_fijo

# Semilla FIJA: garantiza que los sensores simulados sean siempre los mismos
# (mismo "hardware") en todos los experimentos y en todas las ejecuciones.
SEMILLA_SENSORES = 2026

# Número de canales del prototipo (GPIO34, GPIO35, GPIO32).
NUM_SENSORES = 3

# ==========================================
# 3. RUIDO DEL ADC (supuesto de la simulación)
# ==========================================

# Desviación estándar del ruido eléctrico del ADC [cuentas].
# Es un supuesto ("unos pocos pasos"); el ADC real del ESP32 suele ser más ruidoso
# y además no es lineal. Wokwi, en cambio, entrega un ADC ideal sin ruido.
RUIDO_ADC_CUENTAS = 2.0

# Cuenta de un sensor desconectado: el nodo queda pegado a 3V3 y el ADC satura
# en su tope (4095). En saturación el ruido no se observa.
ADC_DESCONECTADO = ADC_MAX

# Límites de lectura válida (los mismos que usa el firmware): una cuenta en los
# extremos indica sensor desconectado (≥ 4090) o en corto (≤ 5).
ADC_LIMITE_INFERIOR = 5
ADC_LIMITE_SUPERIOR = 4090


@dataclass(frozen=True)
class ParametrosSensor:
    """Parámetros físicos (fijos) de un canal de medición."""

    r0_ohm: float      # Resistencia del NTC a T0 [Ω]
    beta_k: float      # Coeficiente β del NTC [K]
    r_fijo_ohm: float  # Resistor fijo del divisor [Ω]

    def como_dict(self):
        return asdict(self)


def generar_parametros_sensores(num_sensores=NUM_SENSORES, semilla=SEMILLA_SENSORES):
    """
    Devuelve una lista con los parámetros de cada sensor, ligeramente distintos
    entre sí y FIJOS (dependen solo de la semilla).
    """
    rng = np.random.default_rng(semilla)

    sensores = []

    for _ in range(num_sensores):
        r0 = R0_NOMINAL_OHM * (1 + rng.uniform(-TOLERANCIA_R0, TOLERANCIA_R0))
        beta = BETA_NOMINAL_K * (1 + rng.uniform(-TOLERANCIA_BETA, TOLERANCIA_BETA))
        r_fijo = R_FIJO_NOMINAL_OHM * (1 + rng.uniform(-TOLERANCIA_R_FIJO, TOLERANCIA_R_FIJO))

        sensores.append(ParametrosSensor(r0_ohm=r0, beta_k=beta, r_fijo_ohm=r_fijo))

    return sensores


# Sensores del prototipo simulado (los mismos en todos los experimentos).
SENSORES = generar_parametros_sensores()

# ==========================================
# 4. CADENA DIRECTA: temperatura -> resistencia -> voltaje -> ADC
# ==========================================


def temperatura_a_resistencia(temperatura_c, r0_ohm, beta_k):
    """Resistencia del NTC [Ω] a la temperatura dada [°C] (ecuación β)."""
    temperatura_k = np.asarray(temperatura_c, dtype=float) + 273.15
    return r0_ohm * np.exp(beta_k * (1.0 / temperatura_k - 1.0 / T0_K))


def resistencia_a_voltaje(resistencia_ohm, r_fijo_ohm, vcc_v=VCC_V):
    """Voltaje del nodo del divisor [V]: 3V3 – R_fijo – nodo – NTC – GND."""
    resistencia_ohm = np.asarray(resistencia_ohm, dtype=float)
    return vcc_v * resistencia_ohm / (r_fijo_ohm + resistencia_ohm)


def voltaje_a_adc_ideal(voltaje_v, vcc_v=VCC_V):
    """Cuenta ADC continua (sin ruido ni redondeo) de un ADC lineal ideal."""
    return np.asarray(voltaje_v, dtype=float) / vcc_v * ADC_MAX


def temperatura_a_adc(
    temperatura_c,
    sensor,
    rng=None,
    ruido_adc_cuentas=RUIDO_ADC_CUENTAS,
    desconectado=False,
):
    """
    Convierte temperatura [°C] en la cuenta ADC entera que leería el ESP32.

    Parámetros
    ----------
    temperatura_c : float o arreglo
        Temperatura real en la posición del sensor [°C].
    sensor : ParametrosSensor
        Parámetros físicos del canal.
    rng : numpy.random.Generator o None
        Generador para el ruido. Si es None no se agrega ruido.
    ruido_adc_cuentas : float
        Desviación estándar del ruido gaussiano del ADC [cuentas].
    desconectado : bool o arreglo de bool
        True donde el NTC está desconectado: la lectura es ≈ 4095.

    Devuelve
    --------
    Arreglo de enteros en [0, 4095].
    """
    temperatura_c = np.asarray(temperatura_c, dtype=float)

    resistencia = temperatura_a_resistencia(temperatura_c, sensor.r0_ohm, sensor.beta_k)
    voltaje = resistencia_a_voltaje(resistencia, sensor.r_fijo_ohm)
    cuenta = voltaje_a_adc_ideal(voltaje)

    if rng is not None and ruido_adc_cuentas > 0:
        ruido = rng.normal(0.0, ruido_adc_cuentas, size=cuenta.shape)
    else:
        ruido = np.zeros_like(cuenta)

    # Sensor desconectado: el nodo queda en 3V3 -> el ADC satura en 4095.
    desconectado = np.broadcast_to(np.asarray(desconectado, dtype=bool), cuenta.shape)
    cuenta = np.where(desconectado, ADC_DESCONECTADO, cuenta + ruido)

    # Redondeo a entero y saturación al rango del ADC.
    cuenta = np.clip(np.rint(cuenta), 0, ADC_MAX).astype(int)

    return cuenta


# ==========================================
# 5. CONVERSIÓN INVERSA PROVISIONAL: ADC -> temperatura (β nominal)
# ==========================================


def adc_a_temperatura_beta(
    adc,
    r0_ohm=R0_NOMINAL_OHM,
    beta_k=BETA_NOMINAL_K,
    r_fijo_ohm=R_FIJO_NOMINAL_OHM,
):
    """
    Conversión PROVISIONAL, SIN CALIBRAR, de cuenta ADC a temperatura [°C]
    usando los parámetros NOMINALES. Es la misma fórmula que usa hoy el firmware.

    Se reemplazará por la calibración propia (R5–R7). Devuelve NaN en las
    lecturas de los extremos del ADC (≤ 5 o ≥ 4090, igual que el firmware),
    que indican sensor en corto o desconectado.
    """
    adc = np.asarray(adc, dtype=float)

    validas = (adc > ADC_LIMITE_INFERIOR) & (adc < ADC_LIMITE_SUPERIOR)
    adc_seguro = np.where(validas, adc, np.nan)

    # Del divisor: adc / ADC_MAX = R_ntc / (R_fijo + R_ntc)
    resistencia = r_fijo_ohm * adc_seguro / (ADC_MAX - adc_seguro)

    temperatura_k = 1.0 / (np.log(resistencia / r0_ohm) / beta_k + 1.0 / T0_K)

    return temperatura_k - 273.15


if __name__ == "__main__":
    # Resumen rápido de los sensores simulados.
    print("Sensores SIMULADOS (semilla fija = %d):" % SEMILLA_SENSORES)
    for i, s in enumerate(SENSORES, start=1):
        print(
            f"  Sensor {i}: R0 = {s.r0_ohm:8.1f} ohm, beta = {s.beta_k:7.1f} K, "
            f"R_fijo = {s.r_fijo_ohm:8.1f} ohm"
        )

    print("\nCuenta ADC sin ruido (sensor 1):")
    for t in [0, 4, 8, 25, 40]:
        print(f"  {t:5.1f} °C -> {int(np.rint(temperatura_a_adc(t, SENSORES[0])))}")
