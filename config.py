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

TIEMPO_ESPERA_AMBULANCIA = 10
TIEMPO_ESPERA_ACCIDENTE = 15

DURACION_AMBAR_PARPADEO = 8
DURACION_VERDE_PRIORITARIO = 25
TIEMPO_TRANSICION_SEGURA = 5

AMBULANCIAS_DISPONIBLES = [
    {"id": "ambulancia_1", "inicio": "edge1", "hospital": "hospital_edge"},
    {"id": "ambulancia_2", "inicio": "edge2", "hospital": "hospital_edge"},
    {"id": "ambulancia_3", "inicio": "edge3", "hospital": "hospital_edge"},
]

VELOCIDAD_AMBULANCIA = 50

