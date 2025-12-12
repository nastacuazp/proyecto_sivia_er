import traceback
import sys
import time
import traci
import os
from pathlib import Path

from config import (
    SUMO_CFG, SUMO_NET, PUERTO_TRACI,
    AMBULANCIAS_DISPONIBLES, TIEMPO_RESPUESTA, ARCHIVO_TRIGGER,
    DURACION_AMBAR_PARPADEO, DURACION_VERDE_PRIORITARIO, TIEMPO_TRANSICION_SEGURA
)

from accident_event.listener import wait_for_accident_event
from routing.graph_loader import cargar_grafo_desde_sumo, obtener_nodos_proximos
from routing.dijkstra import compute_optimal_route
from sumo_interface.traci_manager import GestorTraCI
from sumo_interface.sim_controller import ControladorSimulacion
from traffic_control.controller import ControladorCorredorVerde
from notifications.notifier import Notificador

def obtener_nodos_desde_edges(grafo, edge_inicio_id, edge_destino_id):
    """
    Busca en el grafo los nodos (junctions) que corresponden a los extremos 
    de las calles (edges) indicadas.
    """
    nodo_start = None
    nodo_end = None
    
    # Recorremos las aristas para encontrar qué nodos conectan los edges dados
    for u, v, data in grafo.edges(data=True):
        edge_id = data.get("edge_id")
        
        # Si encontramos la calle de inicio, tomamos el nodo destino 'v' (hacia adelante)
        if edge_id == edge_inicio_id:
            nodo_start = v 
        # Si encontramos la calle destino, tomamos el nodo inicio 'u'
        if edge_id == edge_destino_id:
            nodo_end = u 
        if nodo_start and nodo_end:
            break
            
    return nodo_start, nodo_end

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
        ruta = [punto_partida, punto_llegada]
    
    return ruta

def despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador):
    """
    Ejecuta toda la lógica de cálculo y despacho cuando ocurre el evento.
    Retorna el ID de la ambulancia si tuvo éxito, o None si falló.
    """
    print(f"[MAIN] INICIANDO DESPACHO DE UNIDAD... T={gestor_traci.obtener_tiempo_simulacion()}")
    
    ambulancia = encontrar_ambulancia_cercana(grafo, {})
    if not ambulancia:
        print("[MAIN] Error: No hay ambulancias disponibles")
        return None
        
    ambulancia_id = ambulancia["id"]
    edge_inicio = ambulancia["inicio"]
    edge_destino = ambulancia["hospital"]
    
    print(f"[MAIN] Asignando {ambulancia_id} ({edge_inicio} -> {edge_destino})")

    # Calcular Ruta
    nodo_origen, nodo_destino = obtener_nodos_desde_edges(grafo, edge_inicio, edge_destino)
    if not nodo_origen or not nodo_destino:
        print("[MAIN] Error: No se pudieron traducir los edges a nodos")
        return None
    
    try:
        # Obtenemos la posición (x, y) de la intersección (nodo) destino
        # traci debe estar importado en main.py o accesible
        posicion_accidente = traci.junction.getPosition(nodo_destino)
        
        # Dibujamos el marcador
        gestor_traci.agregar_marcador_accidente(posicion_accidente[0], posicion_accidente[1])
        
    except Exception as e:
        print(f"[MAIN] Advertencia: No se pudo visualizar el accidente: {e}")

    ruta_nodos = calcular_ruta_ambulancia(grafo, nodo_origen, nodo_destino)
    if not ruta_nodos:
        print("[MAIN] Error: No se encontró ruta")
        return None

    # Convertir a Edges
    ruta_edges_traci = [edge_inicio]
    distancia_ruta = 0
    for i in range(len(ruta_nodos)-1):
        u, v = ruta_nodos[i], ruta_nodos[i+1]
        if grafo.has_edge(u, v):
            data = grafo[u][v]
            ruta_edges_traci.append(data.get('edge_id'))
            distancia_ruta += data.get('peso', 0)
    
    if ruta_edges_traci[-1] != edge_destino:
        ruta_edges_traci.append(edge_destino)

    print(f"[MAIN] Ruta calculada: {len(ruta_edges_traci)} tramos, {distancia_ruta}m")

    # Generar en SUMO
    if not gestor_traci.generar_ambulancia(ambulancia_id, edge_inicio, ruta_edges_traci):
        print("[MAIN] Error al crear vehículo en SUMO")
        return None

    # Corredor Verde
    controlador_corredor.execute_green_wave(ruta_edges_traci, ambulancia_id)

    # Notificar
    notificador.send_alert({
        "tipo": "despacho",
        "id_ambulancia": ambulancia_id,
        "destino": edge_destino,
        "ruta": ruta_edges_traci,
        "distancia": distancia_ruta,
        "mensaje": f"Ambulancia {ambulancia_id} despachada tras tiempo de respuesta."
    })

    return ambulancia_id


def ejecutar_simulacion_trigger():
    print("\n" + "="*60)
    print("SISTEMA DE GESTIÓN - ESPERANDO TRIGGER EXTERNO")
    print("="*60 + "\n")
    print(f"[INFO] Ejecute 'python trigger_accident.py' para provocar el accidente.")

    notificador = Notificador(activo=True)
    gestor_traci = GestorTraCI(SUMO_CFG, PUERTO_TRACI, modo_gui=True)
    
    # Limpieza inicial
    if os.path.exists(ARCHIVO_TRIGGER):
        try: os.remove(ARCHIVO_TRIGGER)
        except: pass

    if not gestor_traci.iniciar_sumo():
        return False

    grafo = cargar_grafo_desde_sumo(SUMO_NET)
    controlador_corredor = ControladorCorredorVerde()

    # Estados
    ambulancia_activa = None
    ambulancia_en_ruta = False
    
    # Variables de control
    tiempo_accidente_detectado = None
    tiempo_despacho_programado = None
    ambulancia_despachada = False

    try:
        while True:
            # 1. Avanzar simulación
            if not gestor_traci.avanzar_simulacion(1):
                print("[MAIN] Simulación detenida por SUMO.")
                break
            
            tiempo_actual = gestor_traci.obtener_tiempo_simulacion()

            # 2. ESCUCHAR TRIGGER
            if tiempo_accidente_detectado is None:
                if os.path.exists(ARCHIVO_TRIGGER):
                    try: os.remove(ARCHIVO_TRIGGER)
                    except: pass 
                    
                    tiempo_accidente_detectado = tiempo_actual
                    tiempo_despacho_programado = tiempo_actual + TIEMPO_RESPUESTA
                    
                    print(f"\n[MAIN] 💥 ¡SEÑAL DE ACCIDENTE RECIBIDA! T={tiempo_actual:.1f}")
                    print(f"[MAIN] Iniciando protocolo. Despacho programado para T={tiempo_despacho_programado:.1f}")
                    
                    notificador.send_alert({
                        "tipo": "accidente", 
                        "mensaje": f"Reporte de accidente recibido. Preparando respuesta en {TIEMPO_RESPUESTA}s"
                    })

            # 3. VERIFICAR TIEMPO DE DESPACHO
            if tiempo_despacho_programado and not ambulancia_despachada:
                if tiempo_actual >= tiempo_despacho_programado:
                    ambulancia_activa = despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador)
                    ambulancia_despachada = True

            # 4. SEGUIMIENTO DE AMBULANCIA (CON UBICACIÓN)
            if ambulancia_activa:
                # Llamamos a esto en cada paso para mantener los semáforos en verde
                # mientras la ambulancia se acerca.
                if ambulancia_en_ruta:
                    controlador_corredor.execute_green_wave(None, ambulancia_activa)

                vehiculos_vivos = traci.vehicle.getIDList()
                
                if not ambulancia_en_ruta:
                    if ambulancia_activa in vehiculos_vivos:
                        print(f"[MAIN] 🚑 Unidad {ambulancia_activa} operativa en la vía.")
                        ambulancia_en_ruta = True
                
                elif ambulancia_en_ruta:
                    if ambulancia_activa not in vehiculos_vivos:
                        print(f"[MAIN] ✅ Ambulancia {ambulancia_activa} llegó al destino/hospital.")
                        
                        gestor_traci.eliminar_marcador_accidente()                        
                        notificador.send_alert({"tipo": "fin", "mensaje": "Emergencia finalizada"})
                        
                        # Resetear para permitir otra emergencia
                        ambulancia_activa = None
                        ambulancia_en_ruta = False
                        ambulancia_despachada = False
                        tiempo_accidente_detectado = None
                        tiempo_despacho_programado = None
                        print("[MAIN] Sistema listo para siguiente emergencia...")
                    else:
                        if int(tiempo_actual) % 50 == 0: # Cada 5 segundos aprox
                            try:
                                vel = traci.vehicle.getSpeed(ambulancia_activa)
                                # Obtenemos el ID del borde o cruce actual
                                road_id = traci.vehicle.getRoadID(ambulancia_activa)
                                print(f"[SIM] T={tiempo_actual:.1f} | Pos: {road_id} | Vel: {vel:.1f} m/s")
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
