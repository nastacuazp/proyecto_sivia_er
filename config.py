import os
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS Y ARCHIVOS ---
PROYECTO_ROOT = Path(__file__).parent
SIMULACION_SUMO = "sumo_simulation"

SUMO_CFG = PROYECTO_ROOT / SIMULACION_SUMO / "map.sumocfg"
SUMO_NET = PROYECTO_ROOT / SIMULACION_SUMO / "map.net.xml"
SUMO_ROUTES = PROYECTO_ROOT / SIMULACION_SUMO / "routes.rou.xml"

SUMO_BIN = os.getenv("SUMO_HOME", "/usr/share/sumo") + "/bin/sumo"

# --- CONFIGURACIÓN DE CONEXIÓN ---
PUERTO_TRACI = 8813
#HOST_TRACI = "localhost"

# --- CONFIGURACIÓN DE ACTIVACIÓN ---
ARCHIVO_TRIGGER = "trigger_accidente.flag"

# --- CONFIGURACIÓN DE TIEMPOS ---
#TIEMPO_ESPERA_ACCIDENTE = 0
TIEMPO_RESPUESTA = 10

# --- CONFIGURACIÓN DE SEMÁFOROS (PRIORIDAD) ---
ACTIVAR_PRIORIDAD_SEMAFORICA = True
DISTANCIA_DETECCION_SEMAFORO = 50

# --- CONFIGURACIÓN DE VEHÍCULOS ---
AMBULANCIAS_DISPONIBLES = [
    {"id": "ambulancia_1", "inicio": "421920983#1", "hospital": "24214589#1"}
]

# --- VARIABLES DE CONTROL DE ESCENARIO ---
ACCIDENTE_ID_MANUAL = "cJ3_4" # POSICION DE CAMARA

# Punto de Partida de ambulancia
#EDGE_INICIO_MANUAL = None # Edge de inicio de ambulancia (None = Aleatorio)
EDGE_INICIO_MANUAL = "534500048#0"  # Edge de inicio de ambulancia (Salida fija)

# Modo de Selección de Base (Solo si EDGE_INICIO_MANUAL es None)
# "LEJANIA"  = Selecciona la base más lejana (Simula el peor caso).
# "CERCANIA" = Selecciona la base más cercana (Simula la respuesta óptima).
#MODO_SELECCION_BASE = "CERCANIA"
MODO_SELECCION_BASE = "LEJANIA"

#TIPO_DE_RUTA = "CORTA"
TIPO_DE_RUTA = "LARGA"

