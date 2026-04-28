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
rm almacenador_metricas/registro_metricas.csv
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
en el archivo docker-compose.yml cambiar la distribucion del trafico y la tasa de espera, al bajar ese valor aumenta la cantidad de peticiones por segundo