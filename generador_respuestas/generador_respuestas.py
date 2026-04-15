from statistics import mean
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify

# Definimos una clase para almacenar los datos de cada edificación
class Record:
    def __init__(self, latitude, longitude, area_in_meters, confidence):
        self.latitude = latitude
        self.longitude = longitude
        self.area = area_in_meters 
        self.confidence = confidence

# Simulamos los diccionarios globales donde se cargarán los datos precargados en memoria
data = {}
zone_area_km2 = {}

def carga_datos(ruta_archivo):
    print(f"Cargando dataset desde {ruta_archivo} (esto puede tomar unos segundos)...")
    
    # Leemos el .csv.gz directamente. Ajusta los nombres de las columnas si tu CSV los tiene distintos.
    df = pd.read_csv(ruta_dataset, compression='gzip')

    # Definimos las zonas con los bounding boxes (lat/lon) y un área precalculada en km2 aproximada
    zonas = {
        "Z1": {"nombre": "Providencia", "lat_min": -33.445, "lat_max": -33.420, "lon_min": -70.640, "lon_max": -70.600, "area_km2": 10.5},
        "Z2": {"nombre": "Las Condes", "lat_min": -33.420, "lat_max": -33.390, "lon_min": -70.600, "lon_max": -70.550, "area_km2": 15.6},
        "Z3": {"nombre": "Maipú", "lat_min": -33.530, "lat_max": -33.490, "lon_min": -70.790, "lon_max": -70.740, "area_km2": 21.4},
        "Z4": {"nombre": "Santiago Centro", "lat_min": -33.470, "lat_max": -33.430, "lon_min": -70.670, "lon_max": -70.630, "area_km2": 16.8},
        "Z5": {"nombre": "Pudahuel", "lat_min": -33.460, "lat_max": -33.430, "lon_min": -70.810, "lon_max": -70.760, "area_km2": 15.6}
    }

    for zone_id, limites in zonas.items():
        # Filtramos el dataframe gigante solo para los puntos que caen dentro del rectángulo de esta zona
        filtro = (
            (df['latitude'] >= limites['lat_min']) & (df['latitude'] <= limites['lat_max']) &
            (df['longitude'] >= limites['lon_min']) & (df['longitude'] <= limites['lon_max'])
        )
        df_zona = df[filtro]

        # Llenamos nuestra estructura de memoria con los registros filtrados
        records_zona = []
        for _, row in df_zona.iterrows():
            # Ojo: verifica que los nombres de las columnas en los corchetes coincidan con tu CSV
            records_zona.append(Record(row['latitude'], row['longitude'], row['area_in_meters'], row['confidence']))

        # Guardamos en los diccionarios globales
        data[zone_id] = records_zona
        zone_area_km2[zone_id] = limites['area_km2']
        
        print(f"[{zone_id}] {limites['nombre']}: Se cargaron {len(records_zona)} edificaciones en memoria.")
    

def q1_count(zone_id, confidence_min=0.0):
    """Q1: Conteo de edificaciones en la zona"""
    records = data.get(zone_id, [])
    return sum(1 for r in records if r.confidence >= confidence_min)

def q2_area(zone_id, confidence_min=0.0):
    """Q2: Área promedio y área total de las edificaciones"""
    records = data.get(zone_id, [])
    areas = [r.area for r in records if r.confidence >= confidence_min]
    
    # Validación para evitar dividir por cero si no hay áreas que cumplan el filtro
    if not areas:
        return {"avg_area": 0.0, "total_area": 0.0, "n": 0}
        
    return {"avg_area": mean(areas), "total_area": sum(areas), "n": len(areas)}

def q3_density(zone_id, confidence_min=0.0):
    """Q3: Densidad de las edificaciones por kilómetro cuadrado"""
    count = q1_count(zone_id, confidence_min)
    area_km2 = zone_area_km2.get(zone_id, 0)
    
    # Prevenir división por cero si la zona no tiene área registrada
    if area_km2 == 0:
        return 0.0
    return count / area_km2

def q4_compare(zone_a, zone_b, confidence_min=0.0):
    """Q4: Comparación de densidad entre zonas"""
    da = q3_density(zone_a, confidence_min)
    db = q3_density(zone_b, confidence_min)
    
    return {"zone_a": da, "zone_b": db, "winner": zone_a if da > db else zone_b}

def q5_confidence_dist(zone_id, bins=5):
    """Q5: Distribución de confianza en una zona (Histograma)"""
    records = data.get(zone_id, [])
    scores = [r.confidence for r in records]
    
    # Si no hay registros, retornamos una lista vacía
    if not scores:
        return []

    # Usamos numpy para calcular los bordes y conteos del histograma
    counts, edges = np.histogram(scores, bins=bins, range=(0, 1))
    
    return [
        {
            "bucket": i, 
            "min": float(edges[i]), 
            "max": float(edges[i+1]),
            "count": int(counts[i]) # Casteamos a int nativo de Python para evitar problemas al serializar a JSON después
        } 
        for i in range(bins)
    ]

app = Flask(__name__)

@app.route('/q1', methods=['GET'])
def api_q1():
    # Recibimos los parámetros de la URL (ej: /q1?zone_id=Z1&confidence_min=0.8)
    zone_id = request.args.get('zone_id')
    conf_min = float(request.args.get('confidence_min', 0.0))
    
    resultado = q1_count(zone_id, conf_min)
    return jsonify({"consulta": "Q1", "zona": zone_id, "resultado": resultado})

@app.route('/q2', methods=['GET'])
def api_q2():
    zone_id = request.args.get('zone_id')
    conf_min = float(request.args.get('confidence_min', 0.0))
    
    resultado = q2_area(zone_id, conf_min)
    return jsonify({"consulta": "Q2", "zona": zone_id, "resultado": resultado})

# Puedes replicar esta misma lógica para @app.route('/q3'), '/q4' y '/q5'

if __name__ == '__main__':
    print("Iniciando Generador de Respuestas...")
    ruta_dataset = '967_buildings.csv.gz' 
    
    try:
        # 1. Cargamos el dataset pesado EN MEMORIA una sola vez al arrancar
        carga_datos(ruta_dataset)
        print("Datos cargados. Levantando servidor API en el puerto 5000...")
        
        # 2. Levantamos el servidor para escuchar peticiones de la caché
        # host='0.0.0.0' es crucial en Docker para que acepte conexiones externas al contenedor
        app.run(host='0.0.0.0', port=5000)
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{ruta_dataset}'.")