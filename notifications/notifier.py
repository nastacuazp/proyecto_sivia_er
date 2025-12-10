from datetime import datetime
from typing import Dict, Any
import json

class Notificador:
    def __init__(self, activo: bool = True):
        self.activo = activo
        self.historial = []
    
    def send_alert(self, datos: Dict[str, Any]) -> bool:
        """
        Envía una alerta con los datos del evento.
        Implementación placeholder para futuro bot de Telegram o similar.
        """
        try:
            if not self.activo:
                return False
            
            alerta = {
                "timestamp": datetime.now().isoformat(),
                "tipo": datos.get("tipo", "generico"),
                "id_ambulancia": datos.get("id_ambulancia"),
                "destino": datos.get("destino"),
                "ruta": datos.get("ruta"),
                "distancia": datos.get("distancia"),
                "tiempo_estimado": datos.get("tiempo_estimado"),
                "posicion": datos.get("posicion"),
                "velocidad": datos.get("velocidad"),
                "mensaje": datos.get("mensaje", "")
            }
            
            self.historial.append(alerta)
            self._imprimir_alerta(alerta)
            return True
        except Exception as e:
            print(f"[NOTIFICADOR] Error enviando alerta: {e}")
            return False
    
    def _imprimir_alerta(self, alerta: Dict[str, Any]) -> None:
        """
        Imprime una alerta formateada en consola de forma segura.
        """
        linea_separadora = "=" * 60
        print(linea_separadora)
        print(f"[ALERTA] {alerta['tipo'].upper()}")
        print(f"Timestamp: {alerta['timestamp']}")
        
        if alerta.get('id_ambulancia'):
            print(f"Ambulancia: {alerta['id_ambulancia']}")
        if alerta.get('destino'):
            print(f"Destino: {alerta['destino']}")
            
        ruta = alerta.get('ruta')
        if ruta and isinstance(ruta, list):
            ruta_str = ' -> '.join(str(r) for r in ruta)
            if len(ruta_str) > 100: ruta_str = ruta_str[:97] + "..."
            print(f"Ruta: {ruta_str}")
            
        if alerta.get('distancia') is not None:
            print(f"Distancia: {alerta['distancia']}m")
            
        pos = alerta.get('posicion')
        if pos:
            print(f"Posición actual: {pos}")
            
        vel = alerta.get('velocidad')
        if vel is not None:
            print(f"Velocidad: {vel:.2f} m/s")
            
        if alerta.get('mensaje'):
            print(f"Mensaje: {alerta['mensaje']}")
        print(linea_separadora)
    
    def enviar_notificacion_bot(self, alerta_texto: str, canal_id: str = None) -> bool:
        """
        Placeholder para envío a bot de Telegram o similar.
        """
        print(f"[NOTIFICADOR] [PLACEHOLDER] Envío a bot: {alerta_texto}")
        if canal_id:
            print(f"[NOTIFICADOR] [PLACEHOLDER] Canal: {canal_id}")
        return True
    
    def obtener_historial(self) -> list:
        """
        Retorna el historial de alertas.
        """
        return self.historial
    
    def limpiar_historial(self) -> None:
        """
        Limpia el historial de alertas.
        """
        self.historial = []
