import time
import os
from config import ARCHIVO_TRIGGER

def generar_evento():
    print("="*40)
    print(" 💥 GENERADOR DE EVENTOS DE ACCIDENTE")
    print("="*40)
    
    # Crear el archivo bandera
    with open(ARCHIVO_TRIGGER, "w") as f:
        f.write(f"timestamp={time.time()}|tipo=grave|ubicacion=manual")
        
    print(f"[OK] Señal enviada.")
    print(f"Archivo '{ARCHIVO_TRIGGER}' creado exitosamente.")
    print("La simulación principal debería detectar el accidente en el próximo paso.")

if __name__ == "__main__":
    generar_evento()