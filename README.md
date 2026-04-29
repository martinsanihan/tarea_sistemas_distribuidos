# Tarea Sistemas Distribuidos

Repositorio dedicado al proyecto del ramo de Sistemas Distribuidos, enfocado en construir una plataforma de consultas y respuestas con sistema de caché, gestión de errores y dashboard de visualización.

## Requisitos

1. Instalación de Docker Compose en Linux:
```bash
sudo apt install docker-compose -y
```

## Utilización

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
Primero, obtén los nombres de los contenedores activos:
```bash
sudo docker ps
```
Luego, revisa los logs de un contenedor específico:
```bash
sudo docker compose logs <nombre_del_contenedor>
```
*Ejemplo:*
```bash
sudo docker compose logs almacenador_metricas
```

3. **Ver el estado actual de las métricas:**
Para consultar en tiempo real los *hits*, *misses* y el *hit rate*:
```bash
curl http://localhost:6000/resumen
```

4. **Extraer los registros (CSV):**
Para copiar el archivo de métricas desde el contenedor hacia tu máquina local:
```bash
sudo docker compose cp almacenador_metricas:/app/registro_metricas.csv ./resultados_finales.csv
```

---

## Para el análisis

Todas las modificaciones para los experimentos deben realizarse editando el archivo **`docker-compose.yml`**. 

> ⚠️ **Importante:** Cada vez que modifiques este archivo, debes reiniciar los servicios utilizando `sudo docker compose down && sudo docker volume prune -f` y volver a levantarlos con `sudo docker compose up -d` para que los cambios surtan efecto.

### 1. Modificar el Patrón de Tráfico
Para cambiar el comportamiento de las peticiones, debes modificar el bloque del `generador_trafico`:
*   `DISTRIBUCION`: Cambiar entre `"uniforme"` o `"zipf"`.
*   `TASA_ESPERA`: Modificar para estresar el sistema. Un valor de `0.01` equivale a 100 consultas por segundo aprox. Un valor más bajo genera mayor carga.

**Extracto a modificar en `docker-compose.yml`:**
```yaml
  generador_trafico:
    build: ./generador_trafico
    container_name: generador_trafico
    depends_on:
      - sistema_cache
    environment:
      # Cambiar "uniforme" o "zipf"
      - DISTRIBUCION=uniforme  
      # Cambiar tasa de inyección (ej. 0.01 para estresar el sistema)
      - TASA_ESPERA=0.01       
```

### 2. Modificar el Tamaño del Caché y Políticas de Reemplazo
Para evaluar cómo se comporta la memoria, debes modificar la instrucción `command` dentro del bloque de `cache_redis`:
*   `--maxmemory`: Cambia el límite de memoria (ej. `50mb`, `200mb`, `500mb`).
*   `--maxmemory-policy`: Cambia el algoritmo de desalojo (ej. `allkeys-lru`, `allkeys-lfu`, `allkeys-random`).

**Extracto a modificar en `docker-compose.yml`:**
```yaml
  cache_redis:
    image: redis:latest
    container_name: cache_redis
    ports:
      - "6379:6379"
    # Modificar los valores de maxmemory y maxmemory-policy en esta línea:
    command: redis-server --maxmemory 50mb --maxmemory-policy allkeys-lru 
```

