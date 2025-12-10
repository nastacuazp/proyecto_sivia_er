import traceback
import sys
import time
import traci
from pathlib import Path

from config import (
    SUMO_CFG, SUMO_NET, PUERTO_TRACI, AMBULANCIAS_DISPONIBLES,
    TIEMPO_ESPERA_ACCIDENTE, DURACION_AMBAR_PARPADEO,
    DURACION_VERDE_PRIORITARIO, TIEMPO_TRANSICION_SEGURA, TIEMPO_OCURRENCIA_ACCIDENTE
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
    print(f"\n[MAIN] ⚠ ¡EVENTO DE ACCIDENTE DETECTADO! T={gestor_traci.obtener_tiempo_simulacion()}")
    
    # 1. Crear evento simulado (ya que es por tiempo fijo)
    evento_accidente = {
        "id_interseccion": "junction_simulada",
        "severidad": "alta"
    }
    
    # 2. Seleccionar ambulancia
    ambulancia = encontrar_ambulancia_cercana(grafo, evento_accidente)
    if not ambulancia:
        print("[MAIN] Error: No hay ambulancias disponibles")
        return None
        
    ambulancia_id = ambulancia["id"]
    edge_inicio = ambulancia["inicio"]
    edge_destino = ambulancia["hospital"]
    
    print(f"[MAIN] Asignando {ambulancia_id} ({edge_inicio} -> {edge_destino})")

    # 3. Calcular Ruta
    nodo_origen, nodo_destino = obtener_nodos_desde_edges(grafo, edge_inicio, edge_destino)
    if not nodo_origen or not nodo_destino:
        print("[MAIN] Error: No se pudieron traducir los edges a nodos")
        return None

    ruta_nodos = calcular_ruta_ambulancia(grafo, nodo_origen, nodo_destino)
    if not ruta_nodos:
        print("[MAIN] Error: No se encontró ruta")
        return None

    # 4. Convertir ruta de Nodos a Edges para SUMO
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

    # 5. Generar Ambulancia en SUMO
    if not gestor_traci.generar_ambulancia(ambulancia_id, edge_inicio, ruta_edges_traci):
        print("[MAIN] Error al crear vehículo en SUMO")
        return None

    # 6. Activar Corredor Verde
    # Nota: Si tu controlador necesita los semáforos de la ruta, aquí se procesarían
    controlador_corredor.execute_green_wave(ruta_edges_traci, ambulancia_id)

    # 7. Notificar
    notificador.send_alert({
        "tipo": "despacho",
        "id_ambulancia": ambulancia_id,
        "destino": edge_destino,
        "ruta": ruta_edges_traci,
        "distancia": distancia_ruta,
        "mensaje": f"Ambulancia {ambulancia_id} en camino."
    })

    return ambulancia_id


def ejecutar_simulacion_infinita():
    print("\n" + "="*60)
    print("SISTEMA DE GESTIÓN DE TRÁFICO - MODO CONTINUO")
    print("="*60 + "\n")

    notificador = Notificador(activo=True)
    
    # 1. Iniciar SUMO
    gestor_traci = GestorTraCI(SUMO_CFG, PUERTO_TRACI, modo_gui=True)
    if not gestor_traci.iniciar_sumo():
        return False

    # 2. Cargar Grafo
    grafo = cargar_grafo_desde_sumo(SUMO_NET)
    controlador_corredor = ControladorCorredorVerde()
    controlador_sim = ControladorSimulacion(gestor_traci)

    # Variables de estado
    ambulancia_activa = None
    accidente_procesado = False
    
    print(f"[MAIN] Simulación iniciada. Esperando T={TIEMPO_OCURRENCIA_ACCIDENTE} para accidente...")

    try:
        while True:
            # A. Avanzar simulación un paso
            gestor_traci.avanzar_simulacion(1)
            tiempo_actual = gestor_traci.obtener_tiempo_simulacion()

            # B. Verificar si es momento del accidente
            # Usamos un rango pequeño por si los pasos no son exactos (ej. 50.0 vs 50.1)
            if not accidente_procesado and tiempo_actual >= TIEMPO_OCURRENCIA_ACCIDENTE:
                ambulancia_activa = despachar_emergencia(grafo, gestor_traci, controlador_corredor, notificador)
                accidente_procesado = True # Marcamos para que no se repita infinitamente

            # C. Lógica de seguimiento (si hay ambulancia)
            if ambulancia_activa:
                try:
                    # Verificar si llegó al destino o salió del mapa
                    if ambulancia_activa not in traci.vehicle.getIDList():
                        print(f"[MAIN] Ambulancia {ambulancia_activa} ha llegado a su destino o salido del mapa.")
                        notificador.send_alert({"tipo": "fin", "mensaje": "Emergencia finalizada"})
                        ambulancia_activa = None # Dejar de rastrear
                    else:
                        # Imprimir estado cada 10 segundos simulados
                        if int(tiempo_actual) % 10 == 0:
                            pos = traci.vehicle.getPosition(ambulancia_activa)
                            vel = traci.vehicle.getSpeed(ambulancia_activa)
                            print(f"[SIM] T={tiempo_actual:.1f} | Amb: {pos} | Vel: {vel:.2f} m/s")
                except traci.TraCIException:
                    ambulancia_activa = None

            # D. Condición de salida (opcional, si no hay coches)
            if traci.simulation.getMinExpectedNumber() <= 0 and tiempo_actual > TIEMPO_OCURRENCIA_ACCIDENTE + 100:
                print("[MAIN] No hay más vehículos en la red. Finalizando.")
                break

            # Sleep opcional para no saturar CPU si es muy rápido
            # time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[MAIN] Detenido por el usuario (Ctrl+C)")
    except Exception as e:
        print(f"[MAIN] Error crítico: {e}")
        traceback.print_exc()
    finally:
        gestor_traci.cerrar_conexion()

if __name__ == "__main__":
    try:
        #exito = ejecutar_sistema_emergencias()
        exito = ejecutar_simulacion_infinita()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[MAIN] Error fatal: {e}")
        traceback.print_exc()
        sys.exit(1)
