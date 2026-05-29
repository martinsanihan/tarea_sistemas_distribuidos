from flask import Flask, request, jsonify
import pandas as pd
import time
import os

app = Flask(__name__)

# Archivo donde guardaremos todo el registro histórico
ARCHIVO_LOG = "registro_metricas.csv"

# --- CAMBIO IMPORTANTE: Definimos el orden de las columnas de forma estricta ---
COLUMNAS = ["tipo_evento", "consulta", "zona", "latencia_ms", "timestamp"]

# Si el archivo no existe al arrancar, lo creamos con las cabeceras correctas
if not os.path.exists(ARCHIVO_LOG):
    df_inicial = pd.DataFrame(columns=COLUMNAS)
    df_inicial.to_csv(ARCHIVO_LOG, index=False)

@app.route('/registrar', methods=['POST'])
def registrar_evento():
    # Recibimos los datos en formato JSON
    datos = request.json
    
    # Agregamos la marca de tiempo actual
    datos["timestamp"] = time.time()
    
    # Convertimos a DataFrame
    df = pd.DataFrame([datos])
    
 
    df = df[COLUMNAS]
    
    # Guardamos al final del CSV (mode='a' es append)
    df.to_csv(ARCHIVO_LOG, mode='a', header=False, index=False)
    
    return jsonify({"estado": "registrado"}), 201

@app.route('/resumen', methods=['GET'])
def obtener_resumen():
    if not os.path.exists(ARCHIVO_LOG):
        return jsonify({"error": "No hay métricas aún"})
    
    df = pd.read_csv(ARCHIVO_LOG)
    df['tipo_evento'] = df['tipo_evento'].astype(str).str.strip().str.upper()
    
    total = len(df)
    hits = len(df[df['tipo_evento'] == 'HIT'])
    misses = len(df[df['tipo_evento'] == 'MISS'])
    
    #  nuevas metricas
    retries = len(df[df['tipo_evento'] == 'RETRY'])
    recoveries = len(df[df['tipo_evento'] == 'RECOVERY'])
    dlq = len(df[df['tipo_evento'] == 'DLQ'])
    
    # calculo de percentiles (p50 y p95) solo para consultas exitosas (HIT/MISS)
    df_exitosas = df[df['tipo_evento'].isin(['HIT', 'MISS'])]
    if not df_exitosas.empty:
        p50 = round(df_exitosas['latencia_ms'].quantile(0.50), 2)
        p95 = round(df_exitosas['latencia_ms'].quantile(0.95), 2)
    else:
        p50, p95 = 0, 0
        
    return jsonify({
        "total_peticiones": total,
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hits / total, 4) if total > 0 else 0,
        "retry_rate": round(retries / total, 4) if total > 0 else 0,
        "recovery_rate": round(recoveries / total, 4) if total > 0 else 0,
        "dlq_rate": round(dlq / total, 4) if total > 0 else 0,
        "latencia_p50_ms": p50,
        "latencia_p95_ms": p95
    })
if __name__ == '__main__':
    print("Iniciando Almacenador de Métricas corregido en puerto 6000...")
    app.run(host='0.0.0.0', port=6000)