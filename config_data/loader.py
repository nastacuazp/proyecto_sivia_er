import json
import math
import re
import os
from pathlib import Path

# Rutas a los archivos de configuración
BASE_DIR = Path(__file__).resolve().parent.parent # Asumiendo que loader.py está en /config/ o ajustar según ubicación
CONFIG_DIR = BASE_DIR / "config_data"

def cargar_configuraciones():
    """Carga los 3 archivos JSON de configuración."""
    try:
        with open(CONFIG_DIR / "accident_zones.json", "r") as f:
            zonas = json.load(f)
        with open(CONFIG_DIR / "ambulance_bases.json", "r") as f:
            bases = json.load(f)
        with open(CONFIG_DIR / "exit_edges.json", "r") as f:
            salidas = json.load(f)
        return zonas, bases, salidas
    except FileNotFoundError as e:
        print(f"[CONFIG] Error: No se encontró el archivo {e.filename}")
        return {}, {}, {}

def parsear_coordenadas(junction_id):
    """
    Traduce un ID como 'cJ4a_3' a coordenadas lógicas (x, y).
    Lógica: cJ{COLUMNA}{SUB}_ {FILA}
    """
    # Regex para capturar: (Numero Columna) (Letras opcionales) _ (Numero Fila)
    patron = r"cJ(\d+)([a-z]*)_(\d+)"
    match = re.match(patron, junction_id)
    
    if not match:
        print(f"[CONFIG] Advertencia: ID {junction_id} no sigue el formato esperado.")
        return 0, 0

    col_num = int(match.group(1))
    sub_zona = match.group(2) # 'a', 'b', 'ab' o vacío
    fila_num = int(match.group(3))

    # Ajuste fino para subzonas (opcional, para desempatar distancias)
    # a = izquierda (-0.2), b = derecha (+0.2), ab = centro (0.0)
    ajuste_x = 0.0
    if sub_zona == 'a': ajuste_x = -0.2
    elif sub_zona == 'b': ajuste_x = 0.2
    
    x = float(col_num) + ajuste_x
    y = float(fila_num)
    
    return x, y

def calcular_distancia(junc1, junc2):
    """Calcula distancia Euclidiana entre dos IDs lógicos."""
    x1, y1 = parsear_coordenadas(junc1)
    x2, y2 = parsear_coordenadas(junc2)
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def seleccionar_base_mas_lejana(id_accidente, bases_data):
    """
    Selecciona la base cuya 'junction_logico' esté más lejos del 'id_accidente'.
    """
    mejor_base_id = None
    max_distancia = -1
    detalles_seleccion = {}

    for base_id, datos in bases_data.items():
        base_junction = datos["junction_logico"]
        dist = calcular_distancia(id_accidente, base_junction)
        
        if dist > max_distancia:
            max_distancia = dist
            mejor_base_id = base_id
            detalles_seleccion = datos
            detalles_seleccion["id"] = base_id # Añadimos el ID al dict

    return detalles_seleccion, max_distancia