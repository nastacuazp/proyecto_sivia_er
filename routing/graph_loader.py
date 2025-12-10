import networkx as nx
import xml.etree.ElementTree as ET
from typing import Dict, Tuple
from pathlib import Path

def cargar_grafo_desde_sumo(ruta_net_xml: Path) -> nx.DiGraph:
    """
    Carga el archivo map.net.xml y construye un grafo NetworkX.
    Nodos = intersecciones (junctions)
    Aristas = vías (edges) con peso = longitud
    """
    grafo = nx.DiGraph()
    
    try:
        arbol = ET.parse(ruta_net_xml)
        raiz = arbol.getroot()
        
        junctions = raiz.findall(".//junction")
        for junction in junctions:
            junction_id = junction.get("id")
            x = float(junction.get("x", 0))
            y = float(junction.get("y", 0))
            grafo.add_node(junction_id, x=x, y=y)
        
        edges = raiz.findall(".//edge")
        for edge in edges:
            edge_id = edge.get("id")
            desde = edge.get("from")
            hacia = edge.get("to")
            longitud = float(edge.get("length", 100))
            
            if desde and hacia:
                grafo.add_edge(desde, hacia, peso=longitud, edge_id=edge_id)
        
        print(f"[GRAPH_LOADER] Grafo cargado: {grafo.number_of_nodes()} nodos, {grafo.number_of_edges()} aristas")
        return grafo
    
    except Exception as e:
        print(f"[GRAPH_LOADER] Error cargando grafo: {e}")
        return nx.DiGraph()

def obtener_nodos_proximos(grafo: nx.DiGraph, nodo: str, distancia_maxima: float = 500) -> list:
    """
    Obtiene nodos vecinos dentro de una distancia máxima.
    """
    if nodo not in grafo:
        return []
    
    proximos = []
    for otro_nodo in grafo.nodes():
        try:
            longitud_camino = nx.shortest_path_length(grafo, nodo, otro_nodo, weight='peso')
            if longitud_camino <= distancia_maxima:
                proximos.append((otro_nodo, longitud_camino))
        except nx.NetworkXNoPath:
            continue
    
    return sorted(proximos, key=lambda x: x[1])
