import traceback
import traci
import subprocess
import time
import os
from pathlib import Path
from typing import Optional

class GestorTraCI:
    def __init__(self, archivo_config: Path, puerto: int = 8813, modo_gui: bool = False):
        self.archivo_config = str(archivo_config.resolve()) if isinstance(archivo_config, Path) else str(Path(archivo_config).resolve())
        self.puerto = int(puerto)
        self.modo_gui = modo_gui
        self.conexion_activa = False
    
    def iniciar_sumo(self) -> bool:
        """
        Inicia el servidor SUMO y conecta TraCI usando el método robusto traci.start().
        """
        try:
            # 1. Determinar qué binario usar
            binary = "sumo-gui" #if self.modo_gui else "sumo-gui"
            
            # 2. Construir el comando
            # Nota: traci.start espera una lista de argumentos
            comando_sumo = [
                binary,
                "-c", self.archivo_config,
                "--step-length", "0.1",
                "--start", # Inicia la simulación automáticamente sin esperar play
                # Opciones para evitar cierres inesperados o logs molestos
                "--no-warnings", "true",
                "--window-size", "1000,800"
            ]
            
            print(f"[TRACI_MANAGER] Iniciando SUMO: {' '.join(comando_sumo)}")
            
            # 3. Iniciar SUMO usando traci.start
            traci.start(comando_sumo, port=self.puerto, label="sim1")
            
            self.conexion_activa = True
            print("[TRACI_MANAGER] Conexión TraCI establecida correctamente")
            return True
            
        except Exception as e:
            print(f"[TRACI_MANAGER] Error iniciando SUMO: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def avanzar_simulacion(self, pasos: int = 1) -> bool:
        """
        Avanza la simulación SUMO N pasos.
        """
        try:
            for _ in range(pasos):
                traci.simulationStep()
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
            return 0.0
    
    def generar_ambulancia(self, ambulancia_id: str, edge_inicio: str, ruta: list) -> bool:
        """
        Genera una ambulancia en el borde especificado.
        """
        try:
            # Verificar conexión antes de operar
            if not self.conexion_activa:
                return False

            ruta_id = f"ruta_{ambulancia_id}"
            
            # Asegurar que la ruta sean strings puros
            ruta_limpia = [str(e) for e in ruta]
            
            # Crear la ruta
            traci.route.add(ruta_id, ruta_limpia)
            
            # Definir tipo si no existe (fallback)
            try:
                traci.vehicletype.setLength("ambulancia", 7.0)
            except:
                traci.vehicle.add(ambulancia_id, ruta_id, typeID="DEFAULT_VEHTYPE")
            else:
                traci.vehicle.add(ambulancia_id, ruta_id, typeID="ambulancia")
            
            # Configurar vehículo
            traci.vehicle.setSpeedMode(ambulancia_id, 31) # Ignorar algunas reglas de tráfico
            traci.vehicle.setSpeed(ambulancia_id, 50)
            traci.vehicle.setColor(ambulancia_id, (255, 0, 0, 255)) # Rojo
            
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
