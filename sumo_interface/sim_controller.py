import time
from typing import Optional, List
from .traci_manager import GestorTraCI

class ControladorSimulacion:
    def __init__(self, gestor_traci: GestorTraCI):
        self.gestor = gestor_traci
        self.vehiculos_rastreados = {}
        self.posiciones_historial = {}
    
    def ejecutar_simulacion_paso_a_paso(self, duracion_segundos: int = 60, callback=None) -> bool:
        """
        Ejecuta la simulación paso a paso durante una duración especificada.
        """
        try:
            tiempo_inicio = self.gestor.obtener_tiempo_simulacion()
            tiempo_fin = tiempo_inicio + duracion_segundos
            
            while self.gestor.obtener_tiempo_simulacion() < tiempo_fin:
                self.gestor.avanzar_simulacion(1)
                
                if callback:
                    callback(self.gestor.obtener_tiempo_simulacion())
                
                time.sleep(0.01)
            
            print(f"[SIM_CONTROLLER] Simulación completada ({duracion_segundos}s)")
            return True
        except Exception as e:
            print(f"[SIM_CONTROLLER] Error ejecutando simulación: {e}")
            return False
    
    def rastrear_vehiculo(self, vehiculo_id: str) -> bool:
        """
        Inicia el rastreo de un vehículo.
        """
        try:
            self.vehiculos_rastreados[vehiculo_id] = True
            self.posiciones_historial[vehiculo_id] = []
            print(f"[SIM_CONTROLLER] Rastreando vehículo: {vehiculo_id}")
            return True
        except Exception as e:
            print(f"[SIM_CONTROLLER] Error rastreando: {e}")
            return False
    
    def obtener_datos_rastreo(self, vehiculo_id: str) -> Optional[dict]:
        """
        Obtiene los datos de rastreo actual de un vehículo.
        """
        try:
            if vehiculo_id not in self.vehiculos_rastreados:
                return None
            
            posicion = self.gestor.obtener_posicion_vehiculo(vehiculo_id)
            velocidad = self.gestor.obtener_velocidad_vehiculo(vehiculo_id)
            
            datos = {
                "id": vehiculo_id,
                "posicion": posicion,
                "velocidad": velocidad,
                "tiempo": self.gestor.obtener_tiempo_simulacion()
            }
            
            if vehiculo_id in self.posiciones_historial:
                self.posiciones_historial[vehiculo_id].append(datos)
            
            return datos
        except Exception as e:
            print(f"[SIM_CONTROLLER] Error obteniendo datos: {e}")
            return None
    
    def detener_rastreo(self, vehiculo_id: str) -> bool:
        """
        Detiene el rastreo de un vehículo.
        """
        try:
            if vehiculo_id in self.vehiculos_rastreados:
                del self.vehiculos_rastreados[vehiculo_id]
            
            historial = self.posiciones_historial.get(vehiculo_id, [])
            print(f"[SIM_CONTROLLER] Rastreo detenido: {vehiculo_id} ({len(historial)} puntos)")
            return True
        except Exception as e:
            print(f"[SIM_CONTROLLER] Error deteniendo rastreo: {e}")
            return False
