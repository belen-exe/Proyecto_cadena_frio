
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# 1. CONFIGURACION
# ==========================================

ARCHIVO = "datos_modelo_termico.csv"

# ==========================================
# 2. CARGAR DATOS
# ==========================================

df = pd.read_csv(ARCHIVO)

df = df.sort_values(
    ["Sensor", "Tiempo_min"]
).copy()

# ==========================================
# 3. CREAR VARIABLE OBJETIVO
# ==========================================

# Temperatura del minuto anterior,
# correspondiente al mismo sensor.

df["Temperatura_anterior"] = (
    df.groupby("Sensor")["Temperatura_C"].shift(1)
)

# ==========================================
# 4. CONSTRUIR VARIABLES
# ==========================================

df["Tapa_abierta"] = (
    df["Tapa_abierta"].astype(int)
)

df["Sensor_2"] = (df["Sensor"] == 2).astype(int)
df["Sensor_3"] = (df["Sensor"] == 3).astype(int)

df["Temperatura_anterior_x_tapa"] = (
    df["Temperatura_anterior"] * df["Tapa_abierta"]
)

df["Ambiente_x_tapa"] = (
    df["Temperatura_ambiente_C"] * df["Tapa_abierta"]
)

# Eliminar registros incompletos
df = df.dropna(
    subset=[
        "Temperatura_C",
        "Temperatura_anterior",
        "Temperatura_ambiente_C"
    ]
).copy()

# ==========================================
# 5. DEFINIR MATRIZ X Y VECTOR Y
# ==========================================

columnas_X = [
    "Temperatura_anterior",
    "Temperatura_ambiente_C",
    "Tapa_abierta",
    "Temperatura_anterior_x_tapa",
    "Ambiente_x_tapa",
    "Sensor_2",
    "Sensor_3"
]

X = df[columnas_X].to_numpy(dtype=float)

# Agregar columna de unos para el intercepto
X = np.column_stack([
    np.ones(len(X)),
    X
])

# Temperatura actual: es la que queremos estimar
Y = df["Temperatura_C"].to_numpy(dtype=float)

tiempos = df["Tiempo_min"].to_numpy()

# ==========================================
# 6. SEPARAR ENTRENAMIENTO Y PRUEBA
# ==========================================

tiempo_corte = int(
    df["Tiempo_min"].max() * 0.70
)

indices_entrenamiento = tiempos <= tiempo_corte
indices_prueba = tiempos > tiempo_corte

X_train = X[indices_entrenamiento]
Y_train = Y[indices_entrenamiento]

X_test = X[indices_prueba]
Y_test = Y[indices_prueba]

df_test = df.loc[indices_prueba].copy()

print("========== DIMENSIONES ==========")

print("Matriz X entrenamiento:", X_train.shape)
print("Vector Y entrenamiento:", Y_train.shape)

print("Matriz X prueba:", X_test.shape)
print("Vector Y prueba:", Y_test.shape)

# ==========================================
# 7. REGRESION MATRICIAL
# ==========================================

# Beta = pseudoinversa(X) * Y

beta = np.linalg.pinv(X_train) @ Y_train

print("\n========== COEFICIENTES ==========")

nombres = ["Intercepto"] + columnas_X

for nombre, coeficiente in zip(nombres, beta):

    print(f"{nombre}: {coeficiente:.6f}")

# ==========================================
# 8. PREDICCIONES
# ==========================================

Y_pred = X_test @ beta

df_test["Temperatura_real"] = Y_test
df_test["Temperatura_predicha"] = Y_pred

df_test["Error"] = (
    df_test["Temperatura_real"]
    - df_test["Temperatura_predicha"]
)

# ==========================================
# 9. METRICAS DE EVALUACION
# ==========================================

error_absoluto = np.abs(Y_test - Y_pred)

MAE = np.mean(error_absoluto)

RMSE = np.sqrt(
    np.mean((Y_test - Y_pred) ** 2)
)

SS_res = np.sum((Y_test - Y_pred) ** 2)

SS_tot = np.sum(
    (Y_test - np.mean(Y_test)) ** 2
)

R2 = 1 - (SS_res / SS_tot)

print("\n========== EVALUACION ==========")

print(f"MAE:  {MAE:.4f} °C")
print(f"RMSE: {RMSE:.4f} °C")
print(f"R2:   {R2:.4f}")

# ==========================================
# 10. GUARDAR PREDICCIONES
# ==========================================

df_test.to_csv(
    "predicciones_regresion.csv",
    index=False
)

print("\nArchivo generado: predicciones_regresion.csv")

# ==========================================
# 11. GRAFICA REAL VS PREDICHA
# ==========================================

sensor_grafica = 1

datos_grafica = df_test[
    df_test["Sensor"] == sensor_grafica
]

plt.figure(figsize=(13, 5))

plt.plot(
    datos_grafica["Tiempo_min"],
    datos_grafica["Temperatura_real"],
    label="Temperatura real",
    linewidth=1.5
)

plt.plot(
    datos_grafica["Tiempo_min"],
    datos_grafica["Temperatura_predicha"],
    label="Temperatura predicha",
    linestyle="--",
    linewidth=1.5
)

plt.title(
    f"Regresion matricial - Sensor {sensor_grafica}"
)

plt.xlabel("Tiempo (minutos)")
plt.ylabel("Temperatura (°C)")

plt.legend()
plt.grid()
plt.tight_layout()
plt.show()

# ==========================================
# 12. GRAFICA DE ERRORES
# ==========================================

plt.figure(figsize=(9, 5))

plt.hist(
    df_test["Error"],
    bins=35
)

plt.title("Distribucion de errores de prediccion")
plt.xlabel("Error (°C)")
plt.ylabel("Frecuencia")

plt.grid()
plt.tight_layout()
plt.show()

print("\nRegresion matricial finalizada.")
