from flask import Flask, request, jsonify
import redis
import requests
import json
import time # Añade este import arriba del todo


app = Flask(__name__)

# Conectamos con el contenedor de Redis
# Ojo: 'cache_redis' será el nombre que le daremos al contenedor en el docker-compose
cache = redis.Redis(host='cache_redis', port=6379, decode_responses=True)

# URL base del contenedor del Generador de Respuestas
# 'generador_respuestas' será el nombre del contenedor
RESPUESTAS_URL = 'http://generador_respuestas:5000'
METRICAS_URL = 'http://almacenador_metricas:6000'

# Tiempo de vida de la caché (TTL) en segundos.
TIEMPO_TTL = 2 


@app.route('/consulta', methods=['GET'])
def procesar_consulta():
    inicio_tiempo = time.time()
    
    # Recibimos qué consulta es (q1, q2, etc.) y la zona
    tipo_consulta = request.args.get('tipo')
    zone_id = request.args.get('zone_id')
    conf_val = float(request.args.get('confidence_min', '0.0')) 
    conf_min = ": .1f".format(conf_val) 
    
    if tipo_consulta == 'q1':
        cache_key = f"count:{zone_id}:conf={conf_min}"
        url_destino = f"{RESPUESTAS_URL}/q1?zone_id={zone_id}&confidence_min={conf_min}"
        
    elif tipo_consulta == 'q2':
        cache_key = f"area:{zone_id}:conf={conf_min}"
        url_destino = f"{RESPUESTAS_URL}/q2?zone_id={zone_id}&confidence_min={conf_min}"
        
    elif tipo_consulta == 'q3':
        cache_key = f"density:{zone_id}:conf={conf_min}"
        url_destino = f"{RESPUESTAS_URL}/q3?zone_id={zone_id}&confidence_min={conf_min}"
        
    elif tipo_consulta == 'q4':
        # Q4 usa dos zonas 
        zone_a = request.args.get('zone_a')
        zone_b = request.args.get('zone_b')
        cache_key = f"compare:density:{zone_a}:{zone_b}:conf={conf_min}"
        url_destino = f"{RESPUESTAS_URL}/q4?zone_a={zone_a}&zone_b={zone_b}&confidence_min={conf_min}"
        
        # Actualizamos 'zone_id' para que el almacenador de métricas guarde ambos nombres en el CSV
        zone_id = f"{zone_a}_vs_{zone_b}" 
        
    elif tipo_consulta == 'q5':
        # Q5 usa un parámetro de intervalos (bins), por defecto 5
        bins = request.args.get('bins', '5')
        cache_key = f"confidence_dist:{zone_id}:bins={bins}"
        url_destino = f"{RESPUESTAS_URL}/q5?zone_id={zone_id}&bins={bins}"
        
    else:
        return jsonify({"error": "Consulta no soportada"}), 400

    # Verificar si existe en Caché (Redis)
    resultado_cache = cache.get(cache_key)

    if resultado_cache:
        evento = "HIT"
        print(f"HIT en Caché para: {cache_key}")
        respuesta_final = json.loads(resultado_cache)
    
    else:
        evento = "MISS"
        print(f"MISS en Caché para: {cache_key}. Consultando al Generador...")
        respuesta = requests.get(url_destino)
        datos = respuesta.json()

        # Guardamos el resultado en Redis con un TTL
        cache.set(cache_key, json.dumps(datos), ex=TIEMPO_TTL)

        # Guardamos en la variable, pero NO hacemos 
        respuesta_final = datos
    
    fin_tiempo = time.time()
    latencia = round((fin_tiempo - inicio_tiempo) * 1000, 2)
    datos_metrica = {
        "tipo_evento": evento,
        "consulta": tipo_consulta,
        "zona": zone_id,
        "latencia_ms": latencia
    }
    
    # Intentamos enviarlo al almacenador
    try:
        requests.post(f"{METRICAS_URL}/registrar", json=datos_metrica, timeout=1)
    except:
        print("Advertencia: No se pudo conectar al almacenador de métricas")

    # Finalmente, le respondemos al cliente
    return jsonify(respuesta_final)
    
if __name__ == '__main__':
    print("Iniciando Sistema de Caché interceptor...")
    app.run(host='0.0.0.0', port=4000)  