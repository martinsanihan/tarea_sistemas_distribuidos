from kafka import KafkaConsumer, KafkaProducer
import requests
import json
import time

RESPUESTAS_URL = 'http://generador_respuestas:5000'
METRICAS_URL = 'http://almacenador_metricas:6000'
MAX_RETRIES = 3

def conectar_kafka():
    intentos = 0
    while intentos < 15:
        try:
            print(f"Intentando conectar a Kafka (Intento {intentos + 1})...")
            consumer = KafkaConsumer(
                'topic_reintento',
                bootstrap_servers=['kafka:9092'],
                group_id='group_reintentos',
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

def intentar_procesar(datos):
    # Pausa iterativa para no bombardear un sistema caído (Backoff exponencial simple)
    time.sleep(2 * datos['retry_count'])
    
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

    url_destino = f"{RESPUESTAS_URL}/{tipo_consulta}?zone_id={zone_id}&confidence_min={conf_min}"
    
    try:
        respuesta = requests.get(url_destino, timeout=5)
        respuesta.raise_for_status()
        
        # Si tiene éxito tras reintentar, notificamos la recuperación
        print(f"[RECOVERY] Consulta {datos.get('id_consulta')} recuperada en intento {datos['retry_count']}")
        requests.post(f"{METRICAS_URL}/registrar", json={
            "tipo_evento": "RECOVERY",
            "consulta": tipo_consulta,
            "zona": zone_id,
            "latencia_ms": 0
        }, timeout=1)
        

    except requests.exceptions.RequestException as e:
        if datos['retry_count'] >= MAX_RETRIES:
            print(f"[DLQ] Consulta falló {MAX_RETRIES} veces. Enviando a Dead Letter Queue.")
            producer.send('topic_dlq', value=datos)
            requests.post(f"{METRICAS_URL}/registrar", json={
                "tipo_evento": "DLQ",
                "consulta": tipo_consulta,
                "zona": zone_id,
                "latencia_ms": 0
            }, timeout=1)
        else:
            print(f"[REINTENTO] Falla en intento {datos['retry_count']}. Reencolando...")
            datos['retry_count'] += 1
            producer.send('topic_reintento', value=datos)

if __name__ == '__main__':
    print("Iniciando Consumidor de Reintentos y DLQ...")
    for mensaje in consumer:
        intentar_procesar(mensaje.value)