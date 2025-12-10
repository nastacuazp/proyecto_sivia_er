import time
import random
from datetime import datetime
from typing import Dict, Tuple, Optional

def wait_for_accident_event(timeout_segundos: int = None) -> Optional[Dict]:
    """
    Simula la escucha de un evento de accidente.
    Devuelve un diccionario con ID de intersección, timestamp y coordenadas.
    """
    print("[LISTENER] Esperando evento de accidente...")
    
    if timeout_segundos:
        inicio = time.time()
        while time.time() - inicio < timeout_segundos:
            if random.random() < 0.1:
                break
            time.sleep(1)
    else:
        time.sleep(random.randint(2, 5))
    
    evento = {
        "id_interseccion": f"junction_{random.randint(1, 10)}",
        "timestamp": datetime.now().isoformat(),
        "coordenadas": (random.uniform(0, 1000), random.uniform(0, 1000)),
        "severidad": random.choice(["baja", "media", "alta"])
    }
    
    print(f"[LISTENER] Accidente detectado: {evento}")
    return evento
