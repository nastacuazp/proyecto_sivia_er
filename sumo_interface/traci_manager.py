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
        Genera una ambulancia, asegurando un ID de ruta único para evitar conflictos.
        """
        try:
            if not self.conexion_activa:
                return False

            # --- CORRECCIÓN CLAVE ---
            # Usamos un timestamp para que el ID de la ruta sea único en cada despacho
            # Ejemplo: ruta_ambulancia_1_17005023
            ruta_id = f"ruta_{ambulancia_id}_{int(time.time())}"
            
            ruta_limpia = [str(e) for e in ruta]
            
            # Crear la ruta (ahora el ID es único, así que no fallará)
            traci.route.add(ruta_id, ruta_limpia)

            # Definir o asegurar el tipo de vehículo
            tipo_vehiculo = "ambulancia"
            if tipo_vehiculo not in traci.vehicletype.getIDList():
                try:
                    traci.vehicletype.copy("DEFAULT_VEHTYPE", tipo_vehiculo)
                    traci.vehicletype.setLength(tipo_vehiculo, 6.5)
                    traci.vehicletype.setVehicleClass(tipo_vehiculo, "emergency")
                    traci.vehicletype.setColor(tipo_vehiculo, (255, 0, 0, 255))
                    traci.vehicletype.setShapeClass(tipo_vehiculo, "emergency")
                    traci.vehicletype.setSpeedFactor(tipo_vehiculo, 1.5)
                except Exception as e:
                    print(f"[TRACI] Advertencia configurando tipo: {e}")

            # Limpiar vehículo anterior si existe (reutilización)
            if ambulancia_id in traci.vehicle.getIDList():
                try:
                    traci.vehicle.remove(ambulancia_id)
                except: pass

            # Añadir el vehículo con la NUEVA ruta
            traci.vehicle.add(
                vehID=ambulancia_id,
                routeID=ruta_id,
                typeID=tipo_vehiculo,
                depart="now",
                departLane="best",
                departSpeed="max"
            )
            
            traci.vehicle.setSpeedMode(ambulancia_id, 1)
            
            print(f"[TRACI_MANAGER] Ambulancia {ambulancia_id} generada en {edge_inicio} (Ruta ID: {ruta_id})")
            return True
            
        except Exception as e:
            print(f"[TRACI_MANAGER] Error generando ambulancia: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def agregar_marcador_accidente(self, x: float, y: float):
        """
        Dibuja un marcador visual (POI) en la simulación para indicar el accidente.
        """
        try:
            if not self.conexion_activa:
                return False
                
            # ID del marcador
            poi_id = "marcador_accidente"
            
            # Si ya existe, lo borramos para moverlo
            if poi_id in traci.poi.getIDList():
                traci.poi.remove(poi_id)
            
            # Añadir POI (Punto de Interés)
            # Parámetros: ID, x, y, Color(R,G,B,A), Tipo, Capa, ArchivoImagen, Ancho, Alto
            # Usamos un círculo rojo grande
            traci.poi.add(
                poi_id, 
                x, y, 
                (255, 0, 0, 255),  # Rojo puro
                "accident",        # Tipo
                100,               # Capa (Layer) alta para que se vea sobre las calles
                "",                # Sin imagen (usa forma por defecto o círculo)
                10, 10             # Ancho y Alto (grande para visibilidad)
            )
            
            # Alternativa: Si quisieras un Polígono (ej. un círculo transparente alrededor)
            poly_id = "zona_accidente"
            if poly_id in traci.polygon.getIDList():
                traci.polygon.remove(poly_id)
                
            traci.polygon.add(
                poly_id,
                self._generar_circulo(x, y, 15), # Radio 15m
                (255, 0, 0, 100), # Rojo semitransparente
                fill=True,
                layer=90
            )

            print(f"[TRACI] 📍 Marcador de accidente colocado en ({x:.2f}, {y:.2f})")
            return True
        except Exception as e:
            print(f"[TRACI] Error dibujando marcador: {e}")
            return False

    def _generar_circulo(self, x, y, radio, puntos=30):
        """Genera una lista de coordenadas para dibujar un círculo."""
        import math
        shape = []
        for i in range(puntos):
            angle = 2 * math.pi * i / puntos
            px = x + radio * math.cos(angle)
            py = y + radio * math.sin(angle)
            shape.append((px, py))
        return shape
    
    def eliminar_marcador_accidente(self):
        """Elimina los marcadores visuales del accidente"""
        try:
            if not self.conexion_activa: return False
            
            if "marcador_accidente" in traci.poi.getIDList():
                traci.poi.remove("marcador_accidente")
                
            if "zona_accidente" in traci.polygon.getIDList():
                traci.polygon.remove("zona_accidente")
                
            print("[TRACI] 🗑️ Marcador de accidente eliminado.")
            return True
        except Exception as e:
            print(f"[TRACI] Error eliminando marcador: {e}")
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
