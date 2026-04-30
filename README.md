# Tarea Sistemas Distribuidos

Repositorio dedicado al proyecto del ramo de Sistemas Distribuidos, enfocado en construir una plataforma de consultas y respuestas con sistema de caché, gestión de errores y dashboard de visualización.

## Requisitos

1. Instalación de Docker Compose en Linux:[https://docs.docker.com/engine/install/ubuntu/]
2. Descarga de archivo de datos Google Open Buildings con el comando:
`curl https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/967_buildings.csv.gz -o ./967_buildings.csv.gz`
el comando se debe ejecutar en la carpeta raiz del proyecto.

## Instrucciones de Uso

### Limpieza del entorno
Para eliminar configuraciones previas, detener contenedores y limpiar los archivos generados, ejecuta:
```bash
sudo docker compose down
rm -f resultados_finales.csv
sudo docker volume prune -f
```

### Ejecución y Monitoreo

1. **Iniciar los contenedores:**
```bash
sudo docker compose up --build -d
```

2. **Acceder a los logs internos:**
Primero, se deben obtener los nombres de los contenedores activos:
```bash
sudo docker ps
```
Luego, revisa los logs de un contenedor específico:
```bash
sudo docker compose logs -f <nombre_del_contenedor>
```
*Ejemplo:*
```bash
sudo docker compose logs almacenador_metricas
```

3. **Ver el estado actual de las métricas:**
Para consultar las estadisticas *hits*, *misses* y el *hit rate* en el instante actual:
```bash
curl http://localhost:6000/resumen
```

4. **Extraer los registros (CSV):**
Para copiar el archivo de métricas desde el contenedor hacia tu máquina local:
```bash
sudo docker compose cp almacenador_metricas:/app/registro_metricas.csv ./resultados_finales.csv
```

---

## Análisis

Todas las modificaciones para los experimentos deben realizarse editando el archivo **`docker-compose.yml`**. 

Cada vez que se modifique este archivo, se deben reiniciar los servicios utilizando `sudo docker compose down && sudo docker volume prune -f` y volver a levantarlos con `sudo docker compose up -d` para que los cambios se apliquen.

### 1. Modificar el Patrón de Tráfico
Para cambiar el comportamiento de las peticiones, se debe modificar el bloque del servicio `generador_trafico`:
*   `DISTRIBUCION`: Cambiar entre `"uniforme"` o `"zipf"`.
*   `TASA_ESPERA`: Modificar para estresar el sistema. Un valor de `0.01` equivale a 100 consultas por segundo aprox. Un valor más bajo genera mayor carga.

**Bloque en `docker-compose.yml`:**
```yaml
generador_trafico:
    build: ./generador_trafico
    container_name: generador_trafico
    depends_on:
      - sistema_cache
    environment:
      - DISTRIBUCION=uniforme      # Cambiar "distribución" con el valor (zipf o uniforme) para cambiar distribución de tráfico
      - TASA_ESPERA=0.01        # 0.1 significa 10 peticiones por segundo. bajar este punto estresa más al sistema. subirlo lo hace más relajado.
```

### 2. Modificar el Tamaño del Caché y Políticas de Reemplazo
Para cambiar el comportamiento de la memoria caché, se debe modificar la instrucción `command` dentro del bloque de `cache_redis`:
*   `--maxmemory`: Cambia el límite de memoria (ej. `50mb`, `200mb`, `500mb`).
*   `--maxmemory-policy`: Cambia el algoritmo de desalojo (ej. `allkeys-lru`, `allkeys-lfu`, `allkeys-random`).

**Bloque en `docker-compose.yml`:**
```yaml
  cache_redis:
    image: redis:latest
    container_name: cache_redis
    ports:
      - "6379:6379"
    # Aquí ya configuramos las políticas (LRU y 50mb)
    command: redis-server --maxmemory 50mb --maxmemory-policy allkeys-lru 
```

Ademas dentro del archivo `./sistema_cache/sistema_cache.py` se puede modificar el Time-To-Live de los registros dentro de la memoria caché.

**Bloque en `sistema_cache.py`:**
```python
#...Importación de módulos y definición de constantes

18
19  # Tiempo de vida de la caché (TTL) en segundos.
20  TIEMPO_TTL = 2 
21

# Código...
```

