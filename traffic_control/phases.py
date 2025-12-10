from enum import Enum
from dataclasses import dataclass

class FaseSemanaforo(Enum):
    ROJO = "r"
    AMARILLO = "y"
    VERDE = "g"
    DESACTIVADO = "o"

@dataclass
class EstadoSemanaforo:
    id_semaforo: str
    fase_actual: FaseSemanaforo
    duracion_restante: int
    timestamp: float
