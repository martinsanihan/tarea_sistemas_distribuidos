import time
import requests
import numpy as np
import os
import random

# La URL del caché 
CACHE_URL = "http://sistema_cache:4000/consulta"

ZONAS = ["Z1", "Z2", "Z3", "Z4", "Z5"]
CONSULTAS = ["q1", "q2", "q3", "q4", "q5"]

# Probabilidades Zipf (Ley de Potencia) para 5 elementos
# P(k) proporcional a 1/k. Hace que el 1er elemento sea muy frecuente, y el 5to casi nulo.
pesos_zipf = [1.0 / i for i in range(1, 6)]
probabilidades_zipf = [p / sum(pesos_zipf) for p in pesos_zipf]

def generar_parametros(distribucion):
    if distribucion == "zipf":
        # Simula que todos prefieren consultar la misma zona y la misma query
        zona_principal = np.random.choice(ZONAS, p=probabilidades_zipf)
        tipo_consulta = np.random.choice(CONSULTAS, p=probabilidades_zipf)
        conf_min = 0.5 if random.random() < 0.8 else round(random.random(), 1)
    else:
        # Distribución uniforme: todo es totalmente aleatorio
        zona_principal = random.choice(ZONAS)
        tipo_consulta = random.choice(CONSULTAS)
        # Parámetro de confianza aleatorio entre 0.0 y 0.9 (redondeado a 1 decimal)
        conf_min = round(random.random(), 1) # Esto genera solo 0.1, 0.2, 0.3...

    
    parametros = {
        "tipo": tipo_consulta,
        "zone_id": zona_principal,
        "confidence_min": conf_min
    }

    # Si es Q4, necesitamos una segunda zona distinta a la primera
    if tipo_consulta == "q4":
        zonas_disponibles = [z for z in ZONAS if z != zona_principal]
        parametros["zone_a"] = zona_principal
        parametros["zone_b"] = random.choice(zonas_disponibles)
        del parametros["zone_id"] # Q4 usa a y b en lugar de zone_id
        
    # NO ES AGREGADO Q5 PORQUE LOS BINS VIENE DETERMINADO COMO 5, PODRIA AGREGARSE Y VARIAR ESTE PÁRÁMETRO
        
    return parametros

def iniciar():
    # Leemos la variable de entorno para saber qué distribución usar (por defecto uniforme)
    distribucion = "zipf"
    tasa_espera = 0.01
    
    print(f" Iniciando Generador de Tráfico...")
    print(f"Distribución: {distribucion.upper()}")
    print(f"Enviando 1 petición cada {tasa_espera} segundos.\n")
    
    # Damos 5 segundos para asegurar que el sistema de caché y respuestas ya levantaron
    # time.sleep(5) 
    
    while True:
        params = generar_parametros(distribucion)
        
        try:
            # Disparamos la petición GET al sistema de caché
            respuesta = requests.get(CACHE_URL, params=params, timeout=5)
            
            # Formateamos en consola para ver qué está pasando
            if params['tipo'] == 'q4':
                query_str = f"Q4 ({params['zone_a']} vs {params['zone_b']})"
            else:
                query_str = f"{params['tipo'].upper()} ({params['zone_id']})"
                
            print(f"[ENVIADO] {query_str} | Conf: {params['confidence_min']} | Status: {respuesta.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] No se pudo conectar a la caché: {e}")
            
        time.sleep(tasa_espera)

if __name__ == "__main__":
    iniciar()