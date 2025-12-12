import os
from pathlib import Path

PROYECTO_ROOT = Path(__file__).parent
SIMULACION_SUMO = "sumo_simulation"

SUMO_CFG = PROYECTO_ROOT / SIMULACION_SUMO / "map.sumocfg"
SUMO_NET = PROYECTO_ROOT / SIMULACION_SUMO / "map.net.xml"
SUMO_ROUTES = PROYECTO_ROOT / SIMULACION_SUMO / "routes.rou.xml"

SUMO_BIN = os.getenv("SUMO_HOME", "/usr/share/sumo") + "/bin/sumo"

PUERTO_TRACI = 8813
HOST_TRACI = "localhost"

# Nombre del archivo que servirá como señal de accidente
ARCHIVO_TRIGGER = "trigger_accidente.flag"

# Configuración de Tiempos
TIEMPO_ESPERA_ACCIDENTE = 0
TIEMPO_RESPUESTA = 10

DURACION_AMBAR_PARPADEO = 3
DURACION_VERDE_PRIORITARIO = 10
TIEMPO_TRANSICION_SEGURA = 2

ACTIVAR_PRIORIDAD_SEMAFORICA = True
DISTANCIA_DETECCION_SEMAFORO = 50

AMBULANCIAS_DISPONIBLES = [
    {"id": "ambulancia_1", "inicio": "421920983#1", "hospital": "24214589#1"},
    {"id": "ambulancia_2", "inicio": "534500048#0", "hospital": "24214589#1"},
    {"id": "ambulancia_3", "inicio": "431743797#1", "hospital": "24214589#1"},
]

VELOCIDAD_AMBULANCIA = 50

