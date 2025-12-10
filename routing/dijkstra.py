import heapq
import networkx as nx
from typing import List, Tuple, Optional

def dijkstra_ruta_optima(grafo: nx.DiGraph, nodo_inicio: str, nodo_destino: str) -> Tuple[Optional[List[str]], float]:
    """
    Implementa algoritmo Dijkstra para encontrar la ruta óptima.
    Retorna (lista de nodos, distancia total) o (None, float('inf')) si no hay ruta.
    """
    if nodo_inicio not in grafo or nodo_destino not in grafo:
        return None, float('inf')
    
    distancias = {nodo: float('inf') for nodo in grafo.nodes()}
    distancias[nodo_inicio] = 0
    padres = {nodo: None for nodo in grafo.nodes()}
    
    cola_prioridad = [(0, nodo_inicio)]
    visitados = set()
    
    while cola_prioridad:
        distancia_actual, nodo_actual = heapq.heappop(cola_prioridad)
        
        if nodo_actual in visitados:
            continue
        visitados.add(nodo_actual)
        
        if distancia_actual > distancias[nodo_actual]:
            continue
        
        for vecino in grafo.neighbors(nodo_actual):
            peso_arista = grafo[nodo_actual][vecino].get('peso', 1)
            nueva_distancia = distancia_actual + peso_arista
            
            if nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                padres[vecino] = nodo_actual
                heapq.heappush(cola_prioridad, (nueva_distancia, vecino))
    
    if distancias[nodo_destino] == float('inf'):
        return None, float('inf')
    
    ruta = []
    nodo_actual = nodo_destino
    while nodo_actual is not None:
        ruta.append(nodo_actual)
        nodo_actual = padres[nodo_actual]
    ruta.reverse()
    
    return ruta, distancias[nodo_destino]

def compute_optimal_route(grafo: nx.DiGraph, nodo_inicio: str, nodo_destino: str) -> Optional[List[str]]:
    """
    Interfaz pública para calcular la ruta óptima.
    """
    ruta, distancia = dijkstra_ruta_optima(grafo, nodo_inicio, nodo_destino)
    
    if ruta:
        print(f"[DIJKSTRA] Ruta óptima encontrada: {' -> '.join(ruta)} (distancia: {distancia})")
    else:
        print(f"[DIJKSTRA] No hay ruta disponible entre {nodo_inicio} y {nodo_destino}")
    
    return ruta
