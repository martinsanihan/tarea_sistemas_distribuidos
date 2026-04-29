# tarea_sistemas_distribuidos
Repositorio dedicado al proyecto del ramo sistemas distribuidos, enfocado en construir una plataforma de consultas y respuestas con sistema de cache, gestión de errores y dashboard de visualización.


## Requisitos
1. instalación de compose linux:
```bash
sudo apt install docker-compose -y
```

## Utilización
Para eliminar configuraciones ya hechas
```bash
sudo docker compose down
rm resultados_finales.csv
sudo docker volume prune -f
```


1. Para iniciar los contenedores primero utilizar:
```bash
sudo docker compose up --build -d
```
2. Para acceder a los logs internos de los contenedores utilizar:
Obtiene los nombres de los contenedores
```bash
sudo docker ps
```

```bash
sudo docker compose logs <nombre contenedor>
```

Ejemplo:

```bash
sudo docker compose logs almacenador_metricas
```

3. Ver el estado actual de las metricas como hits, misses y hitrate
```bash
curl http://localhost:6000/resumen
```

4. Ver los registros de las metricas, un archivo csv
```bash
sudo docker compose cp almacenador_metricas:/app/registro_metricas.csv ./resultados_finales.csv
```

## Para el analisis
Debe situarse en el archivo *docker-compose.yml*

Para modifircar el tiempo de distribución cambiar el parámetro *DISTRIBUCIÓN* con "uniforme" o "zipf".

Para cambiar la tasa de peticiones por segundo modificar el parámetro *TASA_ESPERA*, 0.01 equivale a 100 consultas por segundo aprox. Un valor más bajo estresa más  el sistema.
en el apartado de:
   generador_trafico:
    build: ./generador_trafico
    container_name: generador_trafico
    depends_on:
      - sistema_cache
    environment:
      - DISTRIBUCION=uniforme  
      - TASA_ESPERA=0.01       

Para modificar el tamaño del caché modificar el campo *--maxmemory Xmb* y para elegir una política de remplazo distinta cambiar el campo *-maxmemory-policy XXXX* por ejemplo *allkeys-lfu*

En el apartado:
cache_redis:
    image: redis:latest
    container_name: cache_redis
    ports:
      - "6379:6379"
    # Aquí ya configuramos las políticas (LRU y 50mb)
    command: redis-server --maxmemory 50mb --maxmemory-policy allkeys-lru #Cambiar la politica de remplazo para el analisis 

  

