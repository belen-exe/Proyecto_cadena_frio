import pandas as pd
import matplotlib.pyplot as plt

# Leer los datos simulados
archivo = "../Electronica/pruebas_simulacion/mediciones_ntc.csv"

df = pd.read_csv(archivo)

# Mostrar las primeras mediciones
print("Primeras mediciones:")
print(df.head())

# Calcular temperatura promedio por sensor
promedios = df.groupby("Sensor")["Temperatura_C"].mean()

print("\nTemperatura promedio por sensor:")
print(promedios)

# Graficar temperaturas
for sensor in df["Sensor"].unique():
    datos = df[df["Sensor"] == sensor]

    plt.plot(
        datos["Tiempo_ms"],
        datos["Temperatura_C"],
        label=f"Sensor {sensor}"
    )

plt.xlabel("Tiempo (ms)")
plt.ylabel("Temperatura (°C)")
plt.title("Temperatura de los sensores NTC")
plt.legend()
plt.grid()
plt.show()