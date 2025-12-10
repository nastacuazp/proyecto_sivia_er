import traceback
import sys
import time
from pathlib import Path

from config import (
    SUMO_CFG, SUMO_NET, PUERTO_TRACI, AMBULANCIAS_DISPONIBLES,
    TIEMPO_ESPERA_ACCIDENTE, DURACION_AMBAR_PARPADEO,
    DURACION_VERDE_PRIORITARIO, TIEMPO_TRANSICION_SEGURA
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

def ejecutar_sistema_emergencias():
    """
    Función principal que ejecuta el sistema de gestión de emergencias.
    """
    print("\n" + "="*60)
    print("SISTEMA INTELIGENTE DE GESTIÓN DE EMERGENCIAS")
    print("="*60 + "\n")
    
    notificador = Notificador(activo=True)
    
    print("[MAIN] 1. Inicializando SUMO...")
    gestor_traci = GestorTraCI(SUMO_CFG, PUERTO_TRACI, modo_gui=False)
    
    if not gestor_traci.iniciar_sumo():
        print("[MAIN] Error: No se pudo iniciar SUMO")
        return False
    
    print("[MAIN] 2. Cargando grafo de la red...")
    grafo = cargar_grafo_desde_sumo(SUMO_NET)
    
    if grafo.number_of_nodes() == 0:
        print("[MAIN] Error: Grafo vacío, verifique map.net.xml")
        gestor_traci.cerrar_conexion()
        return False
    
    print("[MAIN] 3. Esperando evento de accidente...")
    evento_accidente = wait_for_accident_event(TIEMPO_ESPERA_ACCIDENTE)
    
    if not evento_accidente:
        print("[MAIN] Sin evento de accidente detectado")
        gestor_traci.cerrar_conexion()
        return False
    
    id_interseccion = evento_accidente.get("id_interseccion")
    severidad = evento_accidente.get("severidad")
    
    print(f"[MAIN] 4. Accidente detectado en {id_interseccion} (severidad: {severidad})")
    
    print("[MAIN] 5. Seleccionando ambulancia...")
    ambulancia = encontrar_ambulancia_cercana(grafo, evento_accidente)
    
    if not ambulancia:
        print("[MAIN] Error: No se pudo asignar ambulancia")
        gestor_traci.cerrar_conexion()
        return False
    
    ambulancia_id = ambulancia["id"]
    edge_inicio = ambulancia["inicio"]     
    edge_destino = ambulancia["hospital"]
    
    print("[MAIN] 6. Calculando ruta óptima...")
    nodo_origen, nodo_destino = obtener_nodos_desde_edges(grafo, edge_inicio, edge_destino)
    
    if not nodo_origen or not nodo_destino:
        print(f"[MAIN] Error: No se encontraron intersecciones para las calles {edge_inicio} o {edge_destino}")
        gestor_traci.cerrar_conexion()
        return False
    
    # Calculamos la ruta usando NODOS (Intersecciones)
    ruta_nodos = calcular_ruta_ambulancia(grafo, nodo_origen, nodo_destino)
    
    if not ruta_nodos or len(ruta_nodos) < 2:
        print("[MAIN] Error: No se pudo calcular ruta entre intersecciones")
        gestor_traci.cerrar_conexion()
        return False
    
    # --- Reconstruir lista de Edges y calcular distancia ---
    # TraCI necesita la lista de calles (edges), no de intersecciones
    ruta_edges_traci = [edge_inicio] # La ruta empieza donde está el vehículo
    distancia_ruta = 0
    
    # Recorremos la ruta de nodos para obtener los IDs de los edges y sus pesos
    for i in range(len(ruta_nodos)-1):
        u = ruta_nodos[i]
        v = ruta_nodos[i+1]
        
        # Verificamos que la arista existe (debería, si Dijkstra funcionó)
        if grafo.has_edge(u, v):
            data_edge = grafo[u][v]
            edge_id = data_edge.get('edge_id')
            peso = data_edge.get('peso', 0)
            
            ruta_edges_traci.append(edge_id)
            distancia_ruta += peso
            
    # Añadimos el edge final si no está en la lista (dependiendo de la topología)
    if ruta_edges_traci[-1] != edge_destino:
        ruta_edges_traci.append(edge_destino)

    tiempo_estimado = int(distancia_ruta / 50) if distancia_ruta > 0 else 0
    
    print(f"[MAIN] Ruta (Nodos): {' -> '.join(ruta_nodos)}")
    print(f"[MAIN] Ruta (Edges para SUMO): {' -> '.join(ruta_edges_traci)}")
    print(f"[MAIN] Distancia: {distancia_ruta}m, Tiempo estimado: {tiempo_estimado}s")
    
    print("[MAIN] 7. Generando ambulancia en simulación...")
    # Pasamos a TraCI la lista de EDGES, que es lo que entiende
    if not gestor_traci.generar_ambulancia(ambulancia_id, edge_inicio, ruta_edges_traci):
        print("[MAIN] Error: No se pudo generar ambulancia")
        gestor_traci.cerrar_conexion()
        return False
    
    print("[MAIN] 8. Inicializando corredor verde...")
    # Usamos ruta_edges_traci también para el corredor verde
    controlador_corredor = ControladorCorredorVerde()
    
    if not controlador_corredor.initialize_green_wave(ruta_edges_traci):
        print("[MAIN] Error: No se pudo inicializar corredor")
        gestor_traci.cerrar_conexion()
        return False
    
    print("[MAIN] 9. Ejecutando simulación con corredor verde...")
    controlador_sim = ControladorSimulacion(gestor_traci)
    
    controlador_sim.rastrear_vehiculo(ambulancia_id)
    
    datos_alerta = {
        "tipo": "inicio_emergencia",
        "id_ambulancia": ambulancia_id,
        "destino": edge_destino,          # Antes hospital_destino
        "ruta": ruta_edges_traci,         # Antes ruta_ambulancia
        "distancia": distancia_ruta,
        "tiempo_estimado": tiempo_estimado,
        "posicion": (0, 0),
        "velocidad": 0.0,
        "mensaje": f"Ambulancia despachada. Accidente en {id_interseccion}"
    }
    
    notificador.send_alert(datos_alerta)
    
    duracion_simulacion = min(tiempo_estimado + 30, 120)
    
    def callback_simulacion(tiempo_actual):
        if int(tiempo_actual) % 10 == 0:
            datos_rastreo = controlador_sim.obtener_datos_rastreo(ambulancia_id)
            if datos_rastreo:
                print(f"[SIM] T={tiempo_actual:.1f}s | Posición: {datos_rastreo['posicion']} | Velocidad: {datos_rastreo['velocidad']:.2f} m/s")
    
    try:
        # Usamos ruta_edges_traci
        controlador_corredor.execute_green_wave(ruta_edges_traci, ambulancia_id)
        
        controlador_sim.ejecutar_simulacion_paso_a_paso(duracion_simulacion, callback_simulacion)
        
        print("[MAIN] 10. Simulación completada")
        
        # --- CORRECCIÓN DE VARIABLES AQUÍ TAMBIÉN ---
        datos_alerta_final = {
            "tipo": "emergencia_completada",
            "id_ambulancia": ambulancia_id,
            "destino": edge_destino,      # Antes hospital_destino
            "ruta": ruta_edges_traci,     # Antes ruta_ambulancia
            "distancia": distancia_ruta,
            "tiempo_estimado": tiempo_estimado,
            # obtener_datos_rastreo puede devolver None si el vehículo ya salió, añadir manejo seguro
            "posicion": controlador_sim.obtener_datos_rastreo(ambulancia_id)['posicion'] if controlador_sim.obtener_datos_rastreo(ambulancia_id) else "Destino",
            "velocidad": 0.0,
            "mensaje": "Emergencia procesada exitosamente"
        }
        
        notificador.send_alert(datos_alerta_final)
        
    except KeyboardInterrupt:
        print("\n[MAIN] Simulación interrumpida por usuario")
    except Exception as e:
        print(f"[MAIN] Error durante simulación: {e}")
    finally:
        controlador_sim.detener_rastreo(ambulancia_id)
        print("[MAIN] 11. Cerrando conexión TraCI...")
        gestor_traci.cerrar_conexion()
    
    print("\n[MAIN] Sistema de emergencias finalizado\n")
    
    return True

if __name__ == "__main__":
    try:
        exito = ejecutar_sistema_emergencias()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[MAIN] Error fatal: {e}")
        traceback.print_exc()
        sys.exit(1)
