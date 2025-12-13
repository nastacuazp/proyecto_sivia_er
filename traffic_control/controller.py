import traceback
import traci
import time
from typing import List, Optional
from config import ACTIVAR_PRIORIDAD_SEMAFORICA, DISTANCIA_DETECCION_SEMAFORO

class ControladorCorredorVerde:
    def __init__(self):
        self.tls_original_programs = {}
        self.tls_modificados = set()
        self.semaforos_activos = {}
        self.tiempos_cambio = {}
    
    def initialize_green_wave(self, ruta: List[str]) -> bool:
        """
        Método de compatibilidad. En la nueva lógica dinámica no es estrictamente necesario,
        pero lo mantenemos para evitar errores en main.py si lo llama.
        """
        return True
    
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
        Gestiona la lógica de semáforos si el interruptor está activado.
        """
        if not ACTIVAR_PRIORIDAD_SEMAFORICA:
            return False

        try:
            # Obtener el siguiente semáforo
            next_tls_info = traci.vehicle.getNextTLS(ambulancia_id)
            
            if not next_tls_info:
                return False

            tls_id, tls_index, distancia, estado_actual = next_tls_info[0]

            if distancia <= DISTANCIA_DETECCION_SEMAFORO:
                # GUARDAR PROGRAMA ORIGINAL (SOLO LA PRIMERA VEZ)
                if tls_id not in self.tls_original_programs:
                    try:
                        # Guardamos el ID del programa actual (ej: "0") ANTES de modificarlo
                        prog_original = traci.trafficlight.getProgram(tls_id)
                        self.tls_original_programs[tls_id] = prog_original
                    except:
                        # Si falla, asumimos "0" que es el default de SUMO
                        self.tls_original_programs[tls_id] = "0"

                self._forzar_verde_para_vehiculo(tls_id, ambulancia_id)
                return True
            
            return False

        except Exception as e:
            if "Connection" not in str(e):
                print(f"[CONTROLLER] Error en Green Wave: {e}")
            return False
        
    def _forzar_verde_para_vehiculo(self, tls_id, vehiculo_id):
        """
        Calcula qué índices del semáforo corresponden a la calle de la ambulancia
        y construye un estado donde SOLO esos están en verde.
        """
        try:
            # 1. Obtener en qué carril está la ambulancia
            lane_ambulancia = traci.vehicle.getLaneID(vehiculo_id)
            if not lane_ambulancia: 
                return

            # 2. Obtener los enlaces controlados por el semáforo
            # Esto devuelve una lista de listas. El índice de la lista externa
            # corresponde a la posición en la cadena de luces (G, r, y, etc.)
            links_controlados = traci.trafficlight.getControlledLinks(tls_id)
            
            # 3. Construir el nuevo estado (Empezamos todo en Rojo 'r')
            nuevo_estado = list("r" * len(links_controlados))
            
            encontrado = False
            
            # 4. Buscar qué índice controla mi carril
            for i, conexiones in enumerate(links_controlados):
                # Cada 'i' puede controlar varias conexiones simultáneas
                for conexion in conexiones:
                    # conexion es: (lane_entrada, lane_salida, via_lane)
                    lane_entrada = conexion[0]
                    
                    # Si la conexión viene del carril de la ambulancia 
                    # O viene del mismo "edge" (calle) que la ambulancia
                    if lane_entrada == lane_ambulancia or self._es_mismo_edge(lane_entrada, lane_ambulancia):
                        nuevo_estado[i] = "G" # Poner en Verde Prioritario
                        encontrado = True
            
            if encontrado:
                estado_final = "".join(nuevo_estado)
                # Forzar el estado en SUMO
                traci.trafficlight.setRedYellowGreenState(tls_id, estado_final)
                # print(f"[SEMAFORO] {tls_id} forzado a {estado_final} para {vehiculo_id}")

        except Exception as e:
            print(f"[CONTROLLER] Error forzando luz verde: {e}")
            
    def restaurar_todos_los_semaforos(self):
        """
        Reinicia el programa automático de todos los semáforos modificados.
        """
        if not self.tls_original_programs:
            return

        print(f"[CONTROLLER] 🔄 Restaurando {len(self.tls_original_programs)} semáforos a su ciclo normal...")
        
        for tls_id, prog_original in list(self.tls_original_programs.items()):
            try:
                # Forzamos a SUMO a cargar el programa original ("0")
                # Esto "rompe" el bloqueo manual de setRedYellowGreenState
                traci.trafficlight.setProgram(tls_id, prog_original)
                
                # Opcional: Forzar fase 0 para reiniciar ciclo limpiamente
                # traci.trafficlight.setPhase(tls_id, 0) 
            except Exception as e:
                print(f"[CONTROLLER] Error restaurando {tls_id} al programa '{prog_original}': {e}")
                
                # Fallback: Intentar forzar "0" si el original falló
                try: traci.trafficlight.setProgram(tls_id, "0")
                except: pass
        
        # Limpiamos el registro
        self.tls_original_programs.clear()
        print("[CONTROLLER] ✅ Semáforos desbloqueados.")

    def _es_mismo_edge(self, lane1, lane2):
        """Ayuda a comparar si dos carriles pertenecen a la misma calle base."""
        try:
            return traci.lane.getEdgeID(lane1) == traci.lane.getEdgeID(lane2)
        except:
            return False

    def restaurar_semaforos(self):
        """
        Opcional: Si quisieras restaurar el programa original explícitamente.
        Nota: SUMO restaura el programa automáticamente si dejamos de enviar 
        setRedYellowGreenState, pero tarda un ciclo.
        """
        # Esta lógica se puede expandir si necesitas resetear inmediatamente
        # cuando la ambulancia cruza.
        pass
    
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
