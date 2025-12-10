import traci
import time
from typing import List, Optional

class ControladorCorredorVerde:
    def __init__(self):
        self.semaforos_activos = {}
        self.tiempos_cambio = {}
    
    def initialize_green_wave(self, ruta: List[str]) -> bool:
        """
        Inicializa el corredor verde para una ruta.
        Identifica los semáforos en la ruta.
        """
        try:
            semaforos_ruta = self._obtener_semaforos_ruta(ruta)
            print(f"[CORREDOR_VERDE] Semáforos en ruta: {semaforos_ruta}")
            self.semaforos_activos = {tls: None for tls in semaforos_ruta}
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error inicializando: {e}")
            return False
    
    def set_warning_phase(self, tls_id: str, duracion: int = 8) -> bool:
        """
        Establece fase de advertencia: ámbar parpadeante durante 8 segundos.
        """
        try:
            print(f"[CORREDOR_VERDE] Fase de advertencia para {tls_id}: {duracion}s ámbar")
            program_id = traci.trafficlight.getProgram(tls_id)
            current_phase = traci.trafficlight.getPhase(tls_id)
            
            traci.trafficlight.setPhase(tls_id, (current_phase + 1) % traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0].phases.__len__())
            
            self.tiempos_cambio[tls_id] = time.time() + duracion
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error en fase de advertencia: {e}")
            return False
    
    def set_priority_green(self, tls_id: str, duracion: int = 25) -> bool:
        """
        Establece verde prioritario absoluto para la ambulancia.
        """
        try:
            print(f"[CORREDOR_VERDE] Verde prioritario para {tls_id}: {duracion}s")
            
            fases = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)
            if not fases:
                return False
            
            fase_verde = 0
            for i, fase in enumerate(fases[0].phases):
                if 'G' in fase.state:
                    fase_verde = i
                    break
            
            traci.trafficlight.setPhase(tls_id, fase_verde)
            self.tiempos_cambio[tls_id] = time.time() + duracion
            
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error en verde prioritario: {e}")
            return False
    
    def safe_transition(self, tls_id: str, tiempo_transicion: int = 5) -> bool:
        """
        Realiza transición segura desde verde prioritario a estado normal.
        """
        try:
            print(f"[CORREDOR_VERDE] Transición segura para {tls_id}: {tiempo_transicion}s")
            
            programa = traci.trafficlight.getProgram(tls_id)
            traci.trafficlight.setProgram(tls_id, programa)
            
            self.tiempos_cambio[tls_id] = time.time() + tiempo_transicion
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error en transición segura: {e}")
            return False
    
    def post_recovery_balance(self, tls_id: str) -> bool:
        """
        Recupera el balance de verdes secundarios después de la ambulancia.
        """
        try:
            print(f"[CORREDOR_VERDE] Recuperación y balance para {tls_id}")
            
            programa = traci.trafficlight.getProgram(tls_id)
            traci.trafficlight.setProgram(tls_id, programa)
            
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error en recuperación: {e}")
            return False
    
    def execute_green_wave(self, ruta: List[str], ambulancia_id: str) -> bool:
        """
        Ejecuta el corredor verde completo para una ambulancia a lo largo de la ruta.
        """
        try:
            print(f"[CORREDOR_VERDE] Ejecutando corredor para {ambulancia_id}")
            
            semaforos = self._obtener_semaforos_ruta(ruta)
            
            for tls_id in semaforos:
                self.set_warning_phase(tls_id, 8)
                time.sleep(8)
                
                self.set_priority_green(tls_id, 25)
                time.sleep(25)
                
                self.safe_transition(tls_id, 5)
                time.sleep(5)
                
                self.post_recovery_balance(tls_id)
            
            print(f"[CORREDOR_VERDE] Corredor completado para {ambulancia_id}")
            return True
        except Exception as e:
            print(f"[CORREDOR_VERDE] Error ejecutando corredor: {e}")
            return False
    
    def _obtener_semaforos_ruta(self, ruta: List[str]) -> List[str]:
        """
        Obtiene los semáforos correspondientes a una ruta.
        """
        semaforos = []
        try:
            todos_semaforos = traci.trafficlight.getIDList()
            for nodo in ruta:
                if nodo in todos_semaforos:
                    semaforos.append(nodo)
        except:
            semaforos = [nodo for nodo in ruta if nodo.startswith("junction")]
        
        return semaforos
