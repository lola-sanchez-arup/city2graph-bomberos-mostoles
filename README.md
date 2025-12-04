# City2Graph – Emergencias Bomberos Móstoles

Repositorio que demuestra el uso de herramientas geoespaciales (GeoPandas + City2Graph + NetworkX + PyTorch Geometric) para transformar datos urbanos (hidrantes, piscinas, lagunas, etc.) en grafos analizables, con aplicaciones orientadas a servicios de emergencia, planificación de cobertura, análisis de riesgo, rutas de respuesta, y más.

---

## Estructura del proyecto
```
├── data/
│ ├── hidrantes.geojson
│ ├── piscinas.geojson
│ ├── laguna.geojson
│ └── otros_datasets/ # futuros datasets (estanques, depósitos de agua, etc.)
├── scripts/
│ ├── conexion_hidrantes_piscinas.py
│ ├── conexion_hidrantes_laguna_folium.py
│ └── (otros scripts futuros)
├── outputs/
│ ├── grafico_hidrantes_piscinas.png # gráfico resultante de visualización 
│ ├── hidrantes_piscinas_graph.pt # grafo serializado PyG
│ ├── category_mappings.json # mapeo de variables categóricas
│ ├── scaler.pt # objeto scaler para normalización
│ └── mapa_hidrantes_laguna.html # mapa interactivo Folium
├── README.md
└── requirements.txt
```
---

## Dependencias

Instalar con:

```
pip install -r requirements.txt
```
---

## Scripts

### `src/conexion_hidrantes_piscinas.py`

- Carga los archivos `hidrantes.geojson` y `piscinas.geojson`.  
- Para las piscinas (en formato MultiPolygon), convierte la geometría a punto usando la primera coordenada.  
- Une ambos datasets en un solo GeoDataFrame.  
- Construye un **grafo KNN** usando City2Graph.  
- Prepara features (coordenadas + atributos), las normaliza con `StandardScaler`.  
- Genera un objeto `torch_geometric.data.Data` con `x`, `edge_index`, `edge_attr`.  
- Divide los nodos en train / val / test (máscaras).  
- Guarda outputs en `outputs/`:
  - `hidrantes_piscinas_graph.pt`
  - `category_mappings.json`
  - `scaler.pt`
  - `grafico_hidrantes_piscinas.png` (visualización estática opcional)  
- Visualiza los nodos diferenciando hidrantes (azul) y piscinas (lila).

### `src/conexion_hidrantes_laguna_folium.py`

- Carga `hidrantes.geojson` y `laguna.geojson`.  
- Extrae coordenadas y propiedades de cada punto.  
- Crea un **grafo por proximidad** basado en distancia geográfica con NetworkX (umbral configurable).  
- Añade nodos de tipo hidrante y laguna.  
- Conecta hidrantes entre sí y laguna‑hidrante si están dentro de una distancia máxima.  
- Genera un mapa interactivo con Folium, con marcadores diferenciados y un “layer control” para activar/desactivar capas.  
- Guarda resultado en `outputs/mapa_hidrantes_laguna.html`.

---

##  Casos de uso 

1. **Optimización de rutas de respuesta:** combinar grafo vial + recursos hidráulicos → calcular rutas óptimas desde estación hasta incidente.  
2. **Cobertura hidráulica:** identificar zonas con baja densidad de hidrantes / recursos, evaluar necesidad de refuerzos.  
3. **Análisis espacial de riesgo:** cruzar con datos de edificios, altura, materiales, zonas de riesgo, proximidad a recursos.  
4. **Predicción con GNN:** entrenar modelos para estimar riesgo, demanda de emergencias, tiempos de respuesta, vulnerabilidades.  
5. **Planificación de recursos y evacuación:** simular escenarios de emergencia, recursos disponibles, rutas de evacuación, accesos a agua.  
6. **Mapa interactivo de recursos:** útil para operativos, supervisión, diagnóstico visual, toma de decisiones en campo.
