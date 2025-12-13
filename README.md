# Sistema de Gestión de Emergencias con SUMO

Sistema inteligente de gestión de emergencias que utiliza SUMO (Simulation of Urban MObility) para simular el despacho de ambulancias con optimización de rutas y control de semáforos mediante corredor verde.

## 📋 Descripción

Este proyecto simula un sistema de respuesta a emergencias médicas en un entorno urbano. Cuando se detecta un accidente, el sistema:

1. **Detecta el evento** mediante un sistema de triggers externo
2. **Asigna una ambulancia** disponible más cercana
3. **Calcula la ruta óptima** usando el algoritmo de Dijkstra
4. **Activa un corredor verde** sincronizando semáforos en la ruta
5. **Monitorea en tiempo real** el progreso de la ambulancia
6. **Envía notificaciones** sobre el estado de la emergencia

## 🚀 Características Principales

- ✅ Simulación realista de tráfico urbano con SUMO
- ✅ Algoritmo de Dijkstra para cálculo de rutas óptimas
- ✅ Control dinámico de semáforos (corredor verde)
- ✅ Sistema de despacho automático de ambulancias
- ✅ Visualización en tiempo real con marcadores
- ✅ Sistema de notificaciones de eventos
- ✅ Interfaz TraCI para control de simulación

## 📁 Estructura del Proyecto

```
proyectosiviaer/
├── accident_event/        # Gestión de eventos de accidente
│   └── listener.py        # Escucha de señales de accidente
├── notifications/         # Sistema de notificaciones
│   ├── __init__.py
│   └── notifier.py       # Envío de alertas
├── routing/              # Algoritmos de enrutamiento
│   ├── dijkstra.py       # Implementación de Dijkstra
│   └── graph_loader.py   # Carga del grafo desde SUMO
├── sumo_interface/       # Interfaz con SUMO
│   ├── sim_controller.py # Control de la simulación
│   └── traci_manager.py  # Gestión de conexión TraCI
├── traffic_control/      # Control de tráfico
│   ├── controller.py     # Controlador de corredor verde
│   └── phases.py         # Fases de semáforos
├── sumo_simulation/      # Archivos de configuración SUMO
│   ├── map.sumocfg       # Configuración de la simulación
│   ├── map.net.xml       # Red viaria
│   └── routes.rou.xml    # Rutas de vehículos
├── config.py             # Configuración global
├── main.py               # Script principal
├── trigger_accident.py   # Generador de eventos
└── requirements.txt      # Dependencias Python
```

## 🔧 Requisitos
### Software Requerido

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **SUMO (Simulation of Urban MObility)**
   - Descarga desde: https://www.eclipse.org/sumo/
   
   **Instalación en Ubuntu:**
   ```bash
   sudo add-apt-repository ppa:sumo/stable
   sudo apt-get update
   sudo apt-get install sumo sumo-tools sumo-doc
   ```
   
   **Instalación en Windows:**
   - Descarga el instalador desde la página oficial
   - Agrega SUMO a las variables de entorno (SUMO_HOME)

3. **Configurar SUMO_HOME**
   ```bash
   # Linux/macOS
   export SUMO_HOME="/usr/share/sumo"
   
   # Windows (PowerShell)
   $env:SUMO_HOME="C:\Program Files\SUMO"
   ```

## 📦 Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd proyecto_sivia_er
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   python3 -m venv venv
   
   # Activar en Linux/macOS
   source venv/bin/activate
   
   # Activar en Windows
   venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Uso

### Modo Normal (Trigger Externo)

1. **Iniciar la simulación principal**
   ```bash
   python main.py
   ```
   
   Esto abrirá la interfaz gráfica de SUMO con el mapa cargado y el tráfico simulado.

2. **Generar un evento de accidente** (en otra terminal)
   ```bash
   python trigger_accident.py
   ```
   
   Esto enviará una señal al sistema para despachar una ambulancia.

### Flujo de Ejecución

```
1. Sistema en espera → Tráfico normal
2. trigger_accident.py → Genera evento
3. Sistema detecta señal → Inicia protocolo
4. Tiempo de respuesta → Prepara ambulancia
5. Calcula ruta óptima → Dijkstra
6. Activa corredor verde → Semáforos
7. Despacha ambulancia → Monitoreo en ruta
8. Ambulancia llega → Finaliza emergencia
```

## ⚙️ Configuración

Edita `config.py` para personalizar el comportamiento:

```python
# Tiempo de respuesta antes del despacho (segundos)
TIEMPO_RESPUESTA = 10

# Duración del semáforo en verde para ambulancia (segundos)
DURACION_VERDE_PRIORITARIO = 10

# Velocidad máxima de la ambulancia (km/h)
VELOCIDAD_AMBULANCIA = 50

# Configurar ambulancias disponibles
AMBULANCIAS_DISPONIBLES = [
    {"id": "ambulancia_1", "inicio": "421920983#1", "hospital": "24214589#1"},
    {"id": "ambulancia_2", "inicio": "534500048#0", "hospital": "24214589#1"},
    {"id": "ambulancia_3", "inicio": "431743797#1", "hospital": "24214589#1"},
]
```

## 📊 Salida del Sistema

El sistema genera logs detallados en la consola:

```
[MAIN] INICIANDO DESPACHO DE UNIDAD... T=45.0
[MAIN] Asignando ambulancia_1 (421920983#1 -> 24214589#1)
[MAIN] Ruta calculada: 8 tramos, 1250m
[MAIN] 🚑 Unidad ambulancia_1 operativa en la vía.
[SIM] T=50.0 | Pos: 421920983#1 | Vel: 13.9 m/s
[CORREDOR] Activando semáforo junction_5 → VERDE
[MAIN] ✅ Ambulancia ambulancia_1 llegó al destino/hospital.
```

## 🧪 Características Técnicas

### Algoritmo de Dijkstra
- Encuentra el camino más corto entre el punto de partida y el hospital
- Considera pesos de las aristas (longitud de calles)
- Optimizado para grafos de gran tamaño

### Corredor Verde
- Detecta semáforos en la ruta de la ambulancia
- Cambia fases a ámbar parpadeante → verde
- Restaura estado normal tras el paso del vehículo
- Distancia de detección configurable (50m por defecto)

### Gestión TraCI
- Conexión persistente con SUMO
- Control en tiempo real de vehículos
- Manipulación de semáforos
- Visualización de marcadores POI

## 🐛 Solución de Problemas

### Error: "SUMO_HOME not found"
```bash
export SUMO_HOME="/usr/share/sumo"
# O la ruta donde instalaste SUMO
```

### Error: "No se pudo conectar a TraCI"
- Verifica que el puerto 8813 esté disponible
- Cambia `PUERTO_TRACI` en `config.py` si es necesario

### Ambulancia no aparece
- Verifica que los edge IDs en `config.py` existan en `map.net.xml`
- Comprueba los logs para errores de ruta

## 📚 Dependencias Principales

- **traci**: Interfaz de control de SUMO
- **networkx**: Manejo de grafos y algoritmos
- **sumolib**: Utilidades para archivos SUMO
---