import warnings
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import city2graph
import torch
from torch_geometric.data import Data
import pandas as pd
import json
from sklearn.preprocessing import StandardScaler
import numpy as np
from shapely.geometry import Point, MultiPolygon, Polygon

warnings.filterwarnings("ignore")

def multipolygon_to_point(geom):
    """
    Extrae la PRIMERA coordenada del primer polígono de un MultiPolygon
    y devuelve un Point.
    """
    if isinstance(geom, MultiPolygon):
        poly0 = list(geom.geoms)[0]            # primer polígono
        x, y = poly0.exterior.coords[0][:2]    # primera coordenada
        return Point(x, y)

    elif isinstance(geom, Polygon):
        x, y = geom.exterior.coords[0][:2]
        return Point(x, y)

    else:
        return geom.centroid

def main():
    # ----------------------------
    # 1. CARGAR HIDRANTES
    # ----------------------------
    hidrantes_fp = "hidrantes.geojson"
    gdf_h = gpd.read_file(hidrantes_fp)

    # Aseguramos CRS proyectado
    try:
        gdf_h = gdf_h.to_crs(epsg=25830)
    except:
        print("No se reproyectó hidrantes")

    gdf_h["tipo"] = "hidrante"

    # ----------------------------
    # 2. CARGAR PISCINAS (MultiPolygon → Point)
    # ----------------------------
    piscinas_fp = "piscinas.geojson"
    gdf_p = gpd.read_file(piscinas_fp)

    # reproyección
    try:
        gdf_p = gdf_p.to_crs(epsg=25830)
    except:
        print("No se reproyectó piscinas")

    # Convertir multipolygon → point (primera coordenada)
    gdf_p["geometry"] = gdf_p["geometry"].apply(multipolygon_to_point)
    gdf_p["tipo"] = "piscina"

    # ----------------------------
    # 3. UNIR AMBOS EN UN ÚNICO GeoDataFrame
    # ----------------------------
    gdf = pd.concat([gdf_h, gdf_p], ignore_index=True)

    # Grafo KNN
    G = city2graph.knn_graph(gdf, k=5, distance_metric="euclidean", as_nx=True)

    gdf = gdf.loc[list(G.nodes())].reset_index(drop=True)

    pos = {i: (geom.x, geom.y) for i, geom in enumerate(gdf.geometry)}

    # ----------------------------
    # 4. FEATURES
    # ----------------------------
    df_attrs = gdf.drop(columns="geometry").copy()

    # eliminar columnas de fecha
    fecha_cols = [
        c for c in df_attrs.columns
        if pd.api.types.is_datetime64_any_dtype(df_attrs[c]) or "fecha" in c.lower()
    ]
    df_attrs = df_attrs.drop(columns=fecha_cols, errors="ignore")

    # convertir categóricas a códigos
    category_mappings = {}
    for col in df_attrs.columns:
        if df_attrs[col].dtype == "object":
            df_attrs[col] = df_attrs[col].astype("category")
            category_mappings[col] = dict(enumerate(df_attrs[col].cat.categories))
            df_attrs[col] = df_attrs[col].cat.codes

    df_attrs = df_attrs.fillna(-1)

    coords = pd.DataFrame([pos[n] for n in range(len(gdf))], columns=["x", "y"])
    node_features_df = pd.concat([coords, df_attrs.reset_index(drop=True)], axis=1)

    scaler = StandardScaler()
    node_features_scaled = scaler.fit_transform(node_features_df.values)

    node_features = torch.tensor(node_features_scaled, dtype=torch.float)

    # ----------------------------
    # 5. ARISTAS
    # ----------------------------
    edges = list(G.edges())
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    edge_attr = []
    for u, v in edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        dist = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
        edge_attr.append([dist])
    edge_attr = torch.tensor(edge_attr, dtype=torch.float)

    data = Data(x=node_features, edge_index=edge_index, edge_attr=edge_attr)

    # ----------------------------
    # 6. SPLITS
    # ----------------------------
    num_nodes = data.num_nodes
    indices = np.arange(num_nodes)
    np.random.shuffle(indices)

    train_size = int(0.7 * num_nodes)
    val_size = int(0.15 * num_nodes)

    train_idx = indices[:train_size]
    val_idx = indices[train_size:train_size + val_size]
    test_idx = indices[train_size + val_size:]

    data.train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    data.val_mask = torch.zeros(num_nodes, dtype=torch.bool)
    data.test_mask = torch.zeros(num_nodes, dtype=torch.bool)

    data.train_mask[train_idx] = True
    data.val_mask[val_idx] = True
    data.test_mask[test_idx] = True

    print(data)
    print("Columnas incluidas en x:", list(node_features_df.columns))

    # ----------------------------
    # 7. GUARDAR
    # ----------------------------
    torch.save(data, "hidrantes_piscinas_graph.pt")
    with open("category_mappings.json", "w", encoding="utf-8") as f:
        json.dump(category_mappings, f, ensure_ascii=False, indent=4)
    torch.save(scaler, "scaler.pt")

    print("Grafo guardado en hidrantes_piscinas_graph.pt")

    # ----------------------------
    # 8. VISUALIZACIÓN (hidrante=azul, piscina=lila)
    # ----------------------------
    color_map = []
    for tipo in gdf["tipo"]:
        if tipo == "hidrante":
            color_map.append("blue")
        else:
            color_map.append("purple")

    plt.figure(figsize=(10, 10))
    nx.draw(
        G, pos=pos, node_size=40, node_color=color_map,
        edge_color="grey", alpha=0.6, with_labels=False
    )
    plt.title("Hidrantes (azul) y Piscinas (lila)")
    plt.axis("equal")
    plt.show()


if __name__ == "__main__":
    main()
