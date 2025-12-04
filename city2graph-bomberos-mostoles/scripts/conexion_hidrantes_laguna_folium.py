
import json
import folium
from folium.plugins import MarkerCluster
import networkx as nx
from geopy.distance import geodesic

# -------------------------
# 1. Cargar archivos GeoJSON
# -------------------------
with open("hidrantes.geojson", "r", encoding="utf-8") as f:
    geojson_h = json.load(f)

with open("laguna.geojson", "r", encoding="utf-8") as f:
    geojson_l = json.load(f)

# -------------------------
# Utilidades
# -------------------------
def norm(v, default="Sin dato"):
    """Normaliza valores None, '', espacios, etc."""
    if v is None:
        return default
    if isinstance(v, str):
        v = v.strip()
        return v if v else default
    return v  # números u otros tipos

# -------------------------
# 2. Extraer hidrantes
# -------------------------
hidrantes = []
for feature in geojson_h.get("features", []):
    geom = feature.get("geometry", {})
    if geom.get("type") != "Point":
        continue  # por seguridad

    coords = geom["coordinates"]  # [lon, lat] en WGS84
    props = feature.get("properties", {})

    hidrantes.append({
        "id": props.get("Identificador"),
        "direccion": norm(props.get("Dirección"), "Sin dirección"),
        "estado": norm(props.get("Estado")),
        "tipo": norm(props.get("Tipo")),
        "senalizacion": norm(props.get("Señalización")),
        "racor45": props.get("Racor 45", 0),
        "racor70": props.get("Racor 70", 0),
        "racor100": props.get("Racor 100", 0),
        "presion": norm(props.get("Presión")),
        "comentarios": norm(props.get("Comentarios")),
        "observaciones": norm(props.get("Observaciones GEP")),
        "lat": coords[1],
        "lon": coords[0]
    })

if not hidrantes:
    raise RuntimeError("No se encontraron hidrantes en 'hidrantes.geojson'.")

# -------------------------
# 3. Extraer laguna(s)
# -------------------------
lagunas = []
for idx, feature in enumerate(geojson_l.get("features", []), start=1):
    geom = feature.get("geometry", {})
    if geom.get("type") != "Point":
        continue  # por seguridad: solo puntos
    coords = geom["coordinates"]  # [lon, lat] en WGS84
    props = feature.get("properties", {}) or {}

    lag_id = props.get("Identificador") or props.get("Nombre") or f"Laguna_{idx}"
    lagunas.append({
        "id": lag_id,
        "nombre": norm(props.get("Nombre") or "Laguna"),
        "municipio": norm(props.get("Municipio"), "Sin municipio"),
        "tipo": norm(props.get("Tipo"), "Laguna"),
        "superficie_m2": norm(props.get("Superficie_m2")),
        "profundidad": norm(props.get("Profundidad")),
        "comentarios": norm(props.get("Comentarios")),
        "fecha_actualizacion": norm(props.get("fecha_actualizacion")),
        "lat": coords[1],
        "lon": coords[0]
    })

# -------------------------
# 4. Crear grafo por proximidad
# -------------------------
G = nx.Graph()

# Añadir nodos hidrantes
for h in hidrantes:
    G.add_node(h["id"], pos=(h["lat"], h["lon"]), tipo="hidrante", datos=h)

# Añadir nodos laguna(s)
for lg in lagunas:
    G.add_node(lg["id"], pos=(lg["lat"], lg["lon"]), tipo="laguna", datos=lg)

# Distancia máxima en metros para conectar
max_dist = 300  # ajusta a 500, 1000, etc. si quieres

# Conexiones entre hidrantes
for i in range(len(hidrantes)):
    for j in range(i + 1, len(hidrantes)):
        h1, h2 = hidrantes[i], hidrantes[j]
        dist = geodesic((h1["lat"], h1["lon"]), (h2["lat"], h2["lon"])).meters
        if dist <= max_dist:
            G.add_edge(h1["id"], h2["id"], weight=round(dist, 2), edge_tipo="hidrante-hidrante")

# Conexiones laguna ↔ hidrantes
for lg in lagunas:
    for h in hidrantes:
        dist = geodesic((lg["lat"], lg["lon"]), (h["lat"], h["lon"])).meters
        if dist <= max_dist:
            G.add_edge(lg["id"], h["id"], weight=round(dist, 2), edge_tipo="laguna-hidrante")

# -------------------------
# 5. Crear mapa interactivo
# -------------------------
# Centro del mapa: primer hidrante, si no primera laguna
if hidrantes:
    center_lat, center_lon = hidrantes[0]["lat"], hidrantes[0]["lon"]
elif lagunas:
    center_lat, center_lon = lagunas[0]["lat"], lagunas[0]["lon"]
else:
    raise RuntimeError("No hay puntos para centrar el mapa (ni hidrantes ni lagunas).")

m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# Grupos de capa para diferenciar visualmente
fg_hidrantes = folium.FeatureGroup(name="Hidrantes")
fg_lagunas = folium.FeatureGroup(name="Laguna(s)")

# Cluster solo para hidrantes (suelen ser muchos)
marker_cluster = MarkerCluster(name="Hidrantes (cluster)").add_to(fg_hidrantes)

# --- Añadir hidrantes con popup personalizado ---
for h in hidrantes:
    popup_html = (
        f"<b>Identificador:</b> {h['id']}<br>"
        f"<b>Dirección:</b> {h['direccion']}<br>"
        f"<b>Estado:</b> {h['estado']}<br>"
        f"<b>Tipo:</b> {h['tipo']}<br>"
        f"<b>Señalización:</b> {h['senalizacion']}<br>"
        f"<b>Racores:</b> 45: {h['racor45']} &nbsp;|&nbsp; 70: {h['racor70']} &nbsp;|&nbsp; 100: {h['racor100']}<br>"
        f"<b>Presión:</b> {h['presion']}<br>"
        f"<b>Comentarios:</b> {h['comentarios']}<br>"
        f"<b>Observaciones:</b> {h['observaciones']}"
    )

    folium.Marker(
        location=[h["lat"], h["lon"]],
        popup=folium.Popup(popup_html, max_width=350),
        tooltip=f"ID {h['id']} – {h['direccion']}",
        icon=folium.Icon(color="blue", icon="fire", prefix="fa")  # icono para hidrantes
    ).add_to(marker_cluster)

# --- Añadir laguna(s) con estilo diferenciado ---
for lg in lagunas:
    popup_html = (
        f"<b>Nombre:</b> {lg['nombre']}<br>"
        f"<b>ID:</b> {lg['id']}<br>"
        f"<b>Municipio:</b> {lg['municipio']}<br>"
        f"<b>Tipo:</b> {lg['tipo']}<br>"
        f"<b>Superficie (m²):</b> {lg['superficie_m2']}<br>"
        f"<b>Profundidad:</b> {lg['profundidad']}<br>"
        f"<b>Comentarios:</b> {lg['comentarios']}<br>"
        f"<b>Fecha actualización:</b> {lg['fecha_actualizacion']}"
    )
    # Marker diferenciado (verde, icono "tint")
    folium.Marker(
        location=[lg["lat"], lg["lon"]],
        popup=folium.Popup(popup_html, max_width=350),
        tooltip=f"Laguna – {lg['nombre']}",
        icon=folium.Icon(color="green", icon="tint", prefix="fa")
    ).add_to(fg_lagunas)

# --- Dibujar aristas (conexiones) ---
for edge in G.edges():
    n1, n2 = edge[0], edge[1]
    e = G.edges[edge]
    w = e.get("weight", 0)
    et = e.get("edge_tipo", "hidrante-hidrante")

    # Posiciones
    p1 = G.nodes[n1]["pos"]
    p2 = G.nodes[n2]["pos"]

    # Color según tipo de conexión
    color = "blue" if et == "hidrante-hidrante" else "red"  # laguna-hidrante en rojo
    folium.PolyLine(
        locations=[[p1[0], p1[1]], [p2[0], p2[1]]],
        color=color,
        weight=2,
        tooltip=f"Distancia: {w} m"
    ).add_to(m)

# Añadir las capas al mapa
fg_hidrantes.add_to(m)
fg_lagunas.add_to(m)

# Control de capas (para mostrar/ocultar)
folium.LayerControl().add_to(m)

# -------------------------
# 6. Guardar mapa
# -------------------------
m.save("mapa_hidrantes_laguna.html")
print("Mapa generado: abre 'mapa_hidrantes_laguna.html' en tu navegador.")
