import traceback
import sys
import time
import traci
import os
from pathlib import Path

from config import (
    SUMO_CFG, SUMO_NET, PUERTO_TRACI,
    AMBULANCIAS_DISPONIBLES, TIEMPO_RESPUESTA, ARCHIVO_TRIGGER
)

from accident_event.listener import wait_for_accident_event #eliminar?
from routing.graph_loader import cargar_grafo_desde_sumo, obtener_nodos_proximos
from routing.dijkstra import compute_optimal_route
from sumo_interface.traci_manager import GestorTraCI
from sumo_interface.sim_controller import ControladorSimulacion
from traffic_control.controller import ControladorCorredorVerde
from config_data.loader import cargar_configuraciones, seleccionar_base_mas_lejana
from notifications.notifier import Notificador

# --- VARIABLES GLOBALES DE SELECCIÓN MANUAL ---
ACCIDENTE_ID_MANUAL = "cJ3_4"  # CAMBIAR LUGAR DE CAMARA/ACCIDENTE

EDGE_INICIO_MANUAL = None # Edge de inicio de ambulancia (None = Aleatorio)
# EDGE_INICIO_MANUAL = "431827289#6"  # Edge de inicio de ambulancia (Salida fija)

ZONAS_ACCIDENTE, BASES_AMBULANCIA, SALIDAS = cargar_configuraciones()

def obtener_nodos_desde_edges(grafo, edge_inicio_id, edge_destino_id):
    """
    Busca en el grafo los nodos (junctions) que corresponden a los extremos 
    de las calles (edges) indicadas.
    """
    nodo_start = None
    nodo_end = None
    # Convertimos a string para asegurar comparación
    edge_inicio_id = str(edge_inicio_id)
    
    for u, v, data in grafo.edges(data=True):
        edge_id = str(data.get("edge_id"))
        if edge_id == edge_inicio_id:
            nodo_start = v 
        # No necesitamos buscar el edge_destino_id para el nodo final 
        # si ya tenemos el ID del junction destino desde el JSON
        
    return nodo_start, None

def encontrar_ambulancia_cercana(grafo, evento):
    """
    Encuentra la ambulancia más cercana al nodo del accidente.
    """
    id_interseccion = evento.get("id_interseccion", "junction_1")
    ambulancias_disponibles = [a for a in AMBULANCIAS_DISPONIBLES]
    
    if not ambulancias_disponibles:
        print("[MAIN] No hay ambulancias disponibles")
        return None
    
    ambulancia_elegida = ambulancias_disponibles[0]
    print(f"[MAIN] Ambulancia asignada: {ambulancia_elegida['id']}")
    
    return ambulancia_elegida

def calcular_ruta_ambulancia(grafo, punto_partida, punto_llegada):
    """
    Calcula la ruta óptima para la ambulancia.
    """
    ruta = compute_optimal_route(grafo, punto_partida, punto_llegada)
    
    if not ruta:
        ruta = None
    
    return ruta

def despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador):
    """
    Ejecuta toda la lógica de cálculo y despacho cuando ocurre el evento.
    """
    print(f"[MAIN] 🚑 TIEMPO DE RESPUESTA CUMPLIDO. DESPACHANDO UNIDAD... T={gestor_traci.obtener_tiempo_simulacion()}")
    
    target_accident_junction = ACCIDENTE_ID_MANUAL
    ambulancia_id = "ambulancia_1"
    
    # --- NUEVA LÓGICA DE SELECCIÓN DE INICIO ---
    if EDGE_INICIO_MANUAL is not None:
        # CASO 1: Inicio Manual Forzado
        print(f"[MAIN] ⚠️ Modo Manual Activado: Saliendo desde '{EDGE_INICIO_MANUAL}'")
        edge_inicio = EDGE_INICIO_MANUAL
        datos_base = {"id": "MANUAL", "junction_logico": "N/A"}
        distancia_logica = 0.0
    else:
        # CASO 2: Cálculo Automático (Base más lejana)
        datos_base, distancia_logica = seleccionar_base_mas_lejana(target_accident_junction, BASES_AMBULANCIA)
        
        if not datos_base:
            print("[MAIN] Error: No se encontraron bases de ambulancia configuradas.")
            return None
            
        edge_inicio = datos_base["edge_entrada"]
        print(f"[MAIN] 🏥 Base Automática: {datos_base.get('id')} (Distancia lógica: {distancia_logica:.2f})")
    # ---------------------------------------------

    node_destino_id = target_accident_junction
    print(f"[MAIN] 📍 Destino Accidente: {target_accident_junction}")
    print(f"[MAIN] 🛣️ Ruta prevista: {edge_inicio} -> {node_destino_id}")

    # 1. Calcular Ruta (Nodos)
    nodo_origen, _ = obtener_nodos_desde_edges(grafo, edge_inicio, None)
    
    if not nodo_origen:
        print(f"[MAIN] Error: El edge de inicio '{edge_inicio}' no se encuentra en el grafo o no conecta a ningún nodo.")
        return None

    ruta_nodos = calcular_ruta_ambulancia(grafo, nodo_origen, node_destino_id)
    if not ruta_nodos:
        print("[MAIN] Error: No se encontró ruta física en el grafo entre el inicio y el accidente.")
        return None

    # 2. Convertir a Edges para SUMO
    ruta_edges_traci = [edge_inicio]
    distancia_ruta = 0
    
    for i in range(len(ruta_nodos)-1):
        u, v = ruta_nodos[i], ruta_nodos[i+1]
        if grafo.has_edge(u, v):
            data = grafo[u][v]
            ruta_edges_traci.append(data.get('edge_id'))
            distancia_ruta += data.get('peso', 0)
    
    print(f"[MAIN] Ruta calculada: {len(ruta_edges_traci)} tramos, {distancia_ruta:.1f}m")

    # 3. Visualizar Marcador
    try:
        pos = traci.junction.getPosition(node_destino_id)
        gestor_traci.agregar_marcador_accidente(pos[0], pos[1])
    except Exception as e:
        print(f"[MAIN] Warning visual: {e}")

    # 4. Generar en SUMO
    if not gestor_traci.generar_ambulancia(ambulancia_id, edge_inicio, ruta_edges_traci):
        print("[MAIN] Error al crear vehículo en SUMO")
        return None

    # 5. Activar Corredor Verde
    controlador_corredor.execute_green_wave(ruta_edges_traci, ambulancia_id)

    # 6. Notificar
    origen_msg = f"Base {datos_base.get('id')}" if EDGE_INICIO_MANUAL is None else f"Punto Manual {edge_inicio}"
    
    notificador.send_alert({
        "tipo": "despacho",
        "id_ambulancia": ambulancia_id,
        "destino": node_destino_id,
        "ruta": ruta_edges_traci,
        "distancia": distancia_ruta,
        "mensaje": f"Ambulancia despachada desde {origen_msg}."
    })

    return ambulancia_id


def ejecutar_simulacion_trigger():
    print("\n" + "="*60)
    print("SISTEMA DE GESTIÓN - ESPERANDO TRIGGER EXTERNO")
    print("="*60 + "\n")
    print(f"[INFO] Ejecute 'python trigger_accident.py' para provocar el accidente.")

    notificador = Notificador(activo=True)
    gestor_traci = GestorTraCI(SUMO_CFG, PUERTO_TRACI, modo_gui=True)
    
    if os.path.exists(ARCHIVO_TRIGGER):
        try: os.remove(ARCHIVO_TRIGGER)
        except: pass

    if not gestor_traci.iniciar_sumo():
        return False

    grafo = cargar_grafo_desde_sumo(SUMO_NET)
    controlador_corredor = ControladorCorredorVerde()

    ambulancia_activa = None
    ambulancia_en_ruta = False
    
    tiempo_accidente_detectado = None
    tiempo_despacho_programado = None
    ambulancia_despachada = False

    try:
        while True:
            if not gestor_traci.avanzar_simulacion(1):
                print("[MAIN] Simulación detenida por SUMO.")
                break
            
            tiempo_actual = gestor_traci.obtener_tiempo_simulacion()

            # Trigger
            if tiempo_accidente_detectado is None:
                if os.path.exists(ARCHIVO_TRIGGER):
                    try: os.remove(ARCHIVO_TRIGGER)
                    except: pass 
                    
                    tiempo_accidente_detectado = tiempo_actual
                    tiempo_despacho_programado = tiempo_actual + TIEMPO_RESPUESTA
                    
                    print(f"\n[MAIN] 💥 ¡SEÑAL DE ACCIDENTE RECIBIDA! T={tiempo_actual:.1f}")
                    notificador.send_alert({
                        "tipo": "accidente", 
                        "mensaje": f"Reporte recibido. Despacho en {TIEMPO_RESPUESTA}s"
                    })

            # Despacho
            if tiempo_despacho_programado and not ambulancia_despachada:
                if tiempo_actual >= tiempo_despacho_programado:
                    ambulancia_activa = despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador)
                    ambulancia_despachada = True

            # Seguimiento
            if ambulancia_activa:
                if ambulancia_en_ruta:
                    controlador_corredor.execute_green_wave(None, ambulancia_activa)

                vehiculos_vivos = traci.vehicle.getIDList()
                
                if not ambulancia_en_ruta:
                    if ambulancia_activa in vehiculos_vivos:
                        print(f"[MAIN] 🚑 Unidad {ambulancia_activa} operativa.")
                        ambulancia_en_ruta = True
                
                elif ambulancia_en_ruta:
                    if ambulancia_activa not in vehiculos_vivos:
                        print(f"[MAIN] ✅ Ambulancia {ambulancia_activa} completó la misión.")
                        gestor_traci.eliminar_marcador_accidente()
                        notificador.send_alert({"tipo": "fin", "mensaje": "Misión finalizada"})
                        
                        # Reset
                        ambulancia_activa = None
                        ambulancia_en_ruta = False
                        ambulancia_despachada = False
                        tiempo_accidente_detectado = None
                        tiempo_despacho_programado = None
                        print("[MAIN] Esperando nueva emergencia...")
                    else:
                        if int(tiempo_actual) % 5 == 0:
                            try:
                                vel = traci.vehicle.getSpeed(ambulancia_activa)
                                road_id = traci.vehicle.getRoadID(ambulancia_activa)
                                print(f"[SIM] T={tiempo_actual:.1f} | 📍 {road_id} | Vel: {vel:.1f} m/s")
                            except: pass

    except KeyboardInterrupt:
        print("\n[MAIN] Detenido por usuario.")
    except Exception as e:
        print(f"[MAIN] Error crítico: {e}")
        traceback.print_exc()
    finally:
        gestor_traci.cerrar_conexion()

if __name__ == "__main__":
    try:
        #exito = ejecutar_sistema_emergencias()
        exito = ejecutar_simulacion_trigger()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[MAIN] Error fatal: {e}")
        traceback.print_exc()
        sys.exit(1)
