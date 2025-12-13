import traceback
import sys
import time
import traci
import math
import os
from pathlib import Path

from config import (
    SUMO_CFG, SUMO_NET, PUERTO_TRACI, ARCHIVO_TRIGGER,
    AMBULANCIAS_DISPONIBLES, TIEMPO_RESPUESTA,
    ACCIDENTE_ID_MANUAL, EDGE_INICIO_MANUAL, MODO_SELECCION_BASE, TIPO_DE_RUTA
)

from accident_event.listener import wait_for_accident_event #eliminar?
from routing.graph_loader import cargar_grafo_desde_sumo, obtener_nodos_proximos
from routing.dijkstra import compute_optimal_route
from sumo_interface.traci_manager import GestorTraCI
from sumo_interface.sim_controller import ControladorSimulacion
from traffic_control.controller import ControladorCorredorVerde
from config_data.loader import cargar_configuraciones, seleccionar_base_automatica
from notifications.notifier import Notificador


ZONAS_ACCIDENTE, BASES_AMBULANCIA, SALIDAS = cargar_configuraciones()

def obtener_nodos_desde_edges(grafo, edge_inicio_id, edge_destino_id):
    """
    Busca en el grafo los nodos (junctions) que corresponden a los extremos 
    de las calles (edges) indicadas.
    """
    nodo_start = None
    # Convertimos a string para asegurar comparación
    edge_inicio_id = str(edge_inicio_id)
    
    for u, v, data in grafo.edges(data=True):
        edge_id = str(data.get("edge_id"))
        if edge_id == edge_inicio_id:
            nodo_start = v 
        # No necesitamos buscar el edge_destino_id para el nodo final 
        # si ya tenemos el ID del junction destino desde el JSON
        
    return nodo_start, None

def distancia_euclidiana(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def encontrar_nodo_desvio_lejano(grafo, nodo_inicio, nodo_fin):
    """
    Busca un nodo en el grafo que maximice la distancia total (Inicio->Nodo + Nodo->Fin).
    """
    try:
        pos_inicio = traci.junction.getPosition(nodo_inicio)
        pos_fin = traci.junction.getPosition(nodo_fin)
        
        mejor_nodo = None
        max_distancia = -1
        
        # Iteramos sobre todos los nodos del grafo para encontrar el más lejano
        for nodo in grafo.nodes():
            if nodo == nodo_inicio or nodo == nodo_fin:
                continue
                
            try:
                # Obtenemos posición candidata
                pos_candidato = traci.junction.getPosition(nodo)
                
                # Calculamos cuánto desvío aporta
                dist_a = distancia_euclidiana(pos_inicio, pos_candidato)
                dist_b = distancia_euclidiana(pos_candidato, pos_fin)
                dist_total = dist_a + dist_b
                
                if dist_total > max_distancia:
                    max_distancia = dist_total
                    mejor_nodo = nodo
            except:
                continue
                
        return mejor_nodo
    except Exception as e:
        print(f"[ROUTING] Error buscando desvío: {e}")
        return None

def calcular_ruta_con_estrategia(grafo, nodo_inicio, nodo_fin):
    """
    Calcula la ruta según la estrategia definida en config.py (CORTA o LARGA).
    """
    if TIPO_DE_RUTA == "CORTA":
        # Estrategia Directa (Dijkstra Estándar)
        return compute_optimal_route(grafo, nodo_inicio, nodo_fin)
    
    elif TIPO_DE_RUTA == "LARGA":
        # Estrategia de Desvío (Waypoint)
        print("[ROUTING] 🔄 Estrategia 'LARGA': Calculando desvío...")
        nodo_intermedio = encontrar_nodo_desvio_lejano(grafo, nodo_inicio, nodo_fin)
        
        if not nodo_intermedio:
            print("[ROUTING] Advertencia: No se encontró nodo de desvío. Usando ruta corta.")
            return compute_optimal_route(grafo, nodo_inicio, nodo_fin)
            
        print(f"[ROUTING] 📍 Punto de desvío seleccionado: {nodo_intermedio}")
        
        # Calcular Tramo 1: Inicio -> Desvío
        ruta_1 = compute_optimal_route(grafo, nodo_inicio, nodo_intermedio)
        # Calcular Tramo 2: Desvío -> Fin
        ruta_2 = compute_optimal_route(grafo, nodo_intermedio, nodo_fin)
        
        if ruta_1 and ruta_2:
            # Unir rutas (ruta_2[1:] para no repetir el nodo intermedio)
            return ruta_1 + ruta_2[1:]
        else:
            print("[ROUTING] Error: No se pudo conectar el desvío. Usando ruta corta.")
            return compute_optimal_route(grafo, nodo_inicio, nodo_fin)
            
    return None

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
    return compute_optimal_route(grafo, punto_partida, punto_llegada)

def despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador):
    """
    Ejecuta toda la lógica de cálculo y despacho cuando ocurre el evento.
    """
    print(f"[MAIN] 🚑 TIEMPO DE RESPUESTA CUMPLIDO. DESPACHANDO UNIDAD... T={gestor_traci.obtener_tiempo_simulacion()}")
    
    target_accident_junction = ACCIDENTE_ID_MANUAL 
    ambulancia_id = "ambulancia_1"
    
    # 1. Selección de Base (Origen)
    if EDGE_INICIO_MANUAL is not None:
        print(f"[MAIN] ⚠️ Modo Manual (Config): Saliendo desde '{EDGE_INICIO_MANUAL}'")
        edge_inicio = EDGE_INICIO_MANUAL
        datos_base = {"id": "MANUAL_CFG"}
    else:
        print(f"[MAIN] 🤖 Modo Automático: Buscando base por '{MODO_SELECCION_BASE}'...")
        datos_base, dist_logica = seleccionar_base_automatica(target_accident_junction, BASES_AMBULANCIA, modo=MODO_SELECCION_BASE)
        if not datos_base: return None
        edge_inicio = datos_base["edge_entrada"]
        print(f"[MAIN] 🏥 Base Seleccionada: {datos_base.get('id')} (Dist. Lógica: {dist_logica:.2f})")

    node_destino_id = target_accident_junction
    print(f"[MAIN] 📍 Destino: {target_accident_junction} | Estrategia Ruta: {TIPO_DE_RUTA}")
    
    # DIBUJAR MARCADOR DE BASE (BLANCO)
    try:
        # Obtenemos la coordenada inicial del edge de partida
        # Usamos traci para obtener la forma del carril 0 de ese edge
        shape_inicio = traci.lane.getShape(f"{edge_inicio}_0")
        if shape_inicio:
            x_base, y_base = shape_inicio[0] # Primera coordenada (x, y)
            gestor_traci.agregar_marcador_base(x_base, y_base, activo=False) # BLANCO
    except Exception as e:
        print(f"[MAIN] Warning visual base: {e}")

    # 2. Calcular Ruta Física
    nodo_origen, _ = obtener_nodos_desde_edges(grafo, edge_inicio, None)
    
    if not nodo_origen:
        print(f"[MAIN] Error: Edge inicio '{edge_inicio}' no conecta.")
        return None

    # --- CAMBIO AQUÍ: Llamamos a la nueva función de estrategia ---
    ruta_nodos = calcular_ruta_con_estrategia(grafo, nodo_origen, node_destino_id)
    # -------------------------------------------------------------
    
    if not ruta_nodos:
        print("[MAIN] Error: No hay ruta física disponible.")
        return None

    # 3. Convertir a Edges
    ruta_edges_traci = [edge_inicio]
    distancia_ruta = 0
    for i in range(len(ruta_nodos)-1):
        u, v = ruta_nodos[i], ruta_nodos[i+1]
        if grafo.has_edge(u, v):
            data = grafo[u][v]
            ruta_edges_traci.append(data.get('edge_id'))
            distancia_ruta += data.get('peso', 0)
    
    print(f"[MAIN] Ruta Final: {len(ruta_edges_traci)} tramos, {distancia_ruta:.1f}m")

    # 4. Visualizar y Generar
    try:
        pos = traci.junction.getPosition(node_destino_id)
        gestor_traci.agregar_marcador_accidente(pos[0], pos[1])
    except: pass

    if not gestor_traci.generar_ambulancia(ambulancia_id, edge_inicio, ruta_edges_traci):
        return None

    controlador_corredor.execute_green_wave(ruta_edges_traci, ambulancia_id)

    origen_txt = f"Base {datos_base.get('id')}" if EDGE_INICIO_MANUAL is None else "Manual"
    notificador.send_alert({
        "tipo": "despacho",
        "id_ambulancia": ambulancia_id,
        "destino": node_destino_id,
        "ruta": ruta_edges_traci,
        "distancia": distancia_ruta,
        "mensaje": f"Ambulancia en camino ({origen_txt} - Ruta {TIPO_DE_RUTA})."
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

            if tiempo_accidente_detectado is None:
                if os.path.exists(ARCHIVO_TRIGGER):
                    try: os.remove(ARCHIVO_TRIGGER)
                    except: pass 
                    tiempo_accidente_detectado = tiempo_actual
                    tiempo_despacho_programado = tiempo_actual + TIEMPO_RESPUESTA
                    print(f"\n[MAIN] 💥 ¡SEÑAL DE ACCIDENTE RECIBIDA! T={tiempo_actual:.1f}")
                    notificador.send_alert({"tipo": "accidente", "mensaje": f"Despacho en {TIEMPO_RESPUESTA}s"})

            if tiempo_despacho_programado and not ambulancia_despachada:
                if tiempo_actual >= tiempo_despacho_programado:
                    ambulancia_activa = despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador)
                    ambulancia_despachada = True

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
                        print(f"[MAIN] ✅ Misión completada.")
                        gestor_traci.eliminar_marcador_accidente()
                        gestor_traci.eliminar_marcador_base()
                        controlador_corredor.restaurar_todos_los_semaforos()
                        notificador.send_alert({"tipo": "fin", "mensaje": "Misión finalizada"})
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
