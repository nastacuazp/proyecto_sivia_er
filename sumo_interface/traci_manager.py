import traceback
import traci
import subprocess
import time
import os
from pathlib import Path
from typing import Optional

class GestorTraCI:
    def __init__(self, archivo_config: Path, puerto: int = 8813, modo_gui: bool = False):
        self.archivo_config = archivo_config
        self.puerto = int(puerto)
        self.modo_gui = modo_gui
        self.conexion_activa = False
        self.tiempo_simulacion = 0
    
    def iniciar_sumo(self) -> bool:
        """
        Inicia el servidor SUMO y conecta TraCI.
        """
        try:
            comando_sumo = [
                "sumo-gui" if not self.modo_gui else "sumo-gui",
                "-c", str(self.archivo_config),
                "--remote-port", str(self.puerto),
                "--step-length", "0.1"
            ]
            
            print(f"[TRACI_MANAGER] Iniciando SUMO: {' '.join(comando_sumo)}")
            
            subprocess.Popen(comando_sumo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            #traci.connect("localhost", int(self.puerto))
            traci.connect(port=self.puerto, host="localhost")
            self.conexion_activa = True
            
            print("[TRACI_MANAGER] Conexión TraCI establecida")
            return True
        except Exception as e:
            print(f"[TRACI_MANAGER] Error iniciando SUMO: {e}")
            traceback.print_exc()
            return False
    
    def avanzar_simulacion(self, pasos: int = 1) -> bool:
        """
        Avanza la simulación SUMO N pasos.
        """
        try:
            for _ in range(pasos):
                traci.simulationStep()
                self.tiempo_simulacion += 0.1
            return True
        except Exception as e:
            print(f"[TRACI_MANAGER] Error avanzando simulación: {e}")
            return False
    
    def obtener_tiempo_simulacion(self) -> float:
        """
        Retorna el tiempo actual de simulación.
        """
        try:
            return traci.simulation.getTime()
        except:
            return self.tiempo_simulacion
    
    def generar_ambulancia(self, ambulancia_id: str, edge_inicio: str, ruta: list) -> bool:
        """
        Genera una ambulancia en el borde especificado.
        """
        try:
            ruta_id = f"ruta_{ambulancia_id}"
            
            if ruta_id not in traci.route.getIDList():
                traci.route.add(ruta_id, ruta)
            
            traci.vehicle.add(
                ambulancia_id,
                ruta_id,
                typeID="ambulancia",
                departLane="best"
            )
            
            traci.vehicle.setSpeed(ambulancia_id, 50)
            
            print(f"[TRACI_MANAGER] Ambulancia {ambulancia_id} generada en {edge_inicio}")
            return True
        except Exception as e:
            print(f"[TRACI_MANAGER] Error generando ambulancia: {e}")
            return False
    
    def obtener_posicion_vehiculo(self, vehiculo_id: str) -> Optional[tuple]:
        """
        Obtiene la posición actual del vehículo.
        """
        try:
            return traci.vehicle.getPosition(vehiculo_id)
        except:
            return None
    
    def obtener_velocidad_vehiculo(self, vehiculo_id: str) -> float:
        """
        Obtiene la velocidad actual del vehículo.
        """
        try:
            return traci.vehicle.getSpeed(vehiculo_id)
        except:
            return 0.0
    
    def cerrar_conexion(self) -> bool:
        """
        Cierra la conexión TraCI y limpia recursos.
        """
        try:
            if self.conexion_activa:
                traci.close()
                self.conexion_activa = False
                print("[TRACI_MANAGER] Conexión TraCI cerrada")
            return True
        except Exception as e:
            print(f"[TRACI_MANAGER] Error cerrando conexión: {e}")
            return False
