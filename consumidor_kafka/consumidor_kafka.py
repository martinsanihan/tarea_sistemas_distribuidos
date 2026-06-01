from kafka import KafkaConsumer, KafkaProducer
import redis
import requests
import json
import time

cache = redis.Redis(host='cache_redis', port=6379, decode_responses=True)
RESPUESTAS_URL = 'http://generador_respuestas:5000'
METRICAS_URL = 'http://almacenador_metricas:6000'
TIEMPO_TTL = 10

def conectar_kafka():
    intentos = 0
    while intentos < 15:
        try:
            print(f"Intentando conectar a Kafka (Intento {intentos + 1})...")
            consumer = KafkaConsumer(
                'topic_principal',
                bootstrap_servers=['kafka:9092'],
                group_id='grupo_consumidores_udp',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=['kafka:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("¡Conexión a Kafka establecida exitosamente!")
            return consumer, producer
        except:
            print("Kafka aún no está listo. Esperando 5 segundos...")
            time.sleep(5)
            intentos += 1
    
    raise Exception("No se pudo conectar a Kafka después de varios intentos.")

consumer, producer = conectar_kafka()
        

def procesar_mensaje(mensaje):
    datos = mensaje.value
    inicio_tiempo = time.time()
    
    tipo_consulta = datos.get('tipo')
    zone_id = datos.get('zone_id', datos.get('zone_a', ''))
    conf_min = "{:.1f}".format(datos.get('confidence_min', 0.0))
    
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
        zone_a = datos.get('zone_a')
        zone_b = datos.get('zone_b')
        cache_key = f"compare:density:{zone_a}:{zone_b}:conf={conf_min}"
        url_destino = f"{RESPUESTAS_URL}/q4?zone_a={zone_a}&zone_b={zone_b}&confidence_min={conf_min}"
        
        # Actualizamos 'zone_id' para que el almacenador de métricas guarde ambos nombres en el CSV
        zone_id = f"{zone_a}_vs_{zone_b}" 
        
    elif tipo_consulta == 'q5':
        # Q5 usa un parámetro de intervalos (bins), por defecto 5
        bins = datos.get('bins', '5')
        cache_key = f"confidence_dist:{zone_id}:bins={bins}"
        url_destino = f"{RESPUESTAS_URL}/q5?zone_id={zone_id}&bins={bins}"
        
    else:
        print(f"Error: Consulta no soportada ({tipo_consulta})")
        return

    resultado_cache = cache.get(cache_key)

    if resultado_cache:
        latencia = round((time.time() - inicio_tiempo) * 1000, 2)
        registrar_metrica("HIT", tipo_consulta, zone_id, latencia)
        print(f"HIT en Caché para: {cache_key}")
    else:
        print(f"MISS en Caché para: {cache_key}. Consultando al Generador...")
        try:
            # Simulamos el procesamiento
            respuesta = requests.get(url_destino, timeout=1)
            respuesta.raise_for_status()
            
            # Éxito: Guardar en caché y registrar métrica
            cache.set(cache_key, json.dumps(respuesta.json()), ex=TIEMPO_TTL)
            latencia = round((time.time() - inicio_tiempo) * 1000, 2)
            registrar_metrica("MISS", tipo_consulta, zone_id, latencia)
            
        except requests.exceptions.RequestException as e:
            # FALLA TEMPORAL DEL SISTEMA: Mandar al tópico de reintento
            print(f"[FALLA] Generador caído o saturado. Enviando a topic_reintento. ID: {datos.get('id_consulta')}")
            datos['retry_count'] += 1
            producer.send('topic_reintento', value=datos)
            registrar_metrica("RETRY", tipo_consulta, zone_id, 0) # Métrica de reintento

def registrar_metrica(evento, consulta, zona, latencia):
    try:
        requests.post(f"{METRICAS_URL}/registrar", json={
            "tipo_evento": evento,
            "consulta": consulta,
            "zona": zona,
            "latencia_ms": latencia
        }, timeout=1)
    except:
        pass

if __name__ == '__main__':
    print("Iniciando Consumidor Kafka...")
    for mensaje in consumer:
        procesar_mensaje(mensaje)