# Contador de visitas (Flask + Redis)

Página web que muestra cuántas veces ha sido visitada. Cada recarga suma uno a un contador guardado en **Redis**. Además, registra **qué contenedor** atendió cada visita, lo que la hace ideal para observar qué pasa cuando escalas un servicio a varias réplicas.

> Proyecto con fines exclusivamente educativos. Inspirado en el ejemplo clásico de la guía de inicio de Docker Compose.

---

## Nivel y objetivos de aprendizaje

**Nivel:** inicial.

Al dockerizar esta aplicación vas a practicar:

- Escribir un `Dockerfile` para una aplicación **Python** con dependencias en `requirements.txt`.
- Ordenar las capas para **aprovechar la caché** al instalar dependencias.
- Diferenciar entre el **servidor de desarrollo** de Flask y un **servidor de producción** (Gunicorn).
- Levantar **dos servicios** que se comunican por la **red interna de Compose** usando el nombre del servicio como *hostname*.
- Usar una **imagen oficial** (Redis) sin escribir un `Dockerfile` para ella.
- Persistir los datos de Redis con un **volumen**.
- **Escalar** un servicio a varias réplicas.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 o superior |
| Framework web | Flask 3 |
| Servidor WSGI (producción) | Gunicorn |
| Base de datos clave-valor | Redis 7 u 8 |
| Cliente Redis | `redis` (redis-py) |
| Plantillas | Jinja2 (incluido con Flask) |

---

## Arquitectura

```
 Navegador ──HTTP──▶  web (Flask + Gunicorn, puerto 5000)
                          │
                          │  TCP 6379 (protocolo Redis)
                          ▼
                       redis (base de datos en memoria)
```

- **web**: lee y escribe el contador en Redis en cada petición.
- **redis**: guarda dos claves:
  - `visitas:total` → número entero con el total de visitas.
  - `visitas:por_contenedor` → *hash* con el nombre de host de cada contenedor y sus visitas.

---

## Estructura del proyecto

```
02-contador-visitas-flask-redis/
├── app.py               # Aplicación Flask (rutas y conexión a Redis)
├── requirements.txt     # Dependencias de Python con versiones fijas
├── templates/
│   └── index.html       # Plantilla Jinja2 de la página principal
├── README.md
└── CHANGELOG.md
```

Detalles importantes:

- **`app.py`**
  - El cliente Redis se crea al importar el módulo, leyendo `REDIS_HOST` y `REDIS_PORT`. **Si no defines `REDIS_HOST`, intentará conectarse a `localhost`**, lo cual dentro de un contenedor apunta *al propio contenedor*, no a Redis.
  - `registrar_visita()` usa un *pipeline* para incrementar ambas claves en un solo viaje de red.
  - `socket.gethostname()` devuelve el nombre de host; dentro de Docker ese valor es el ID corto del contenedor.
  - El bloque `if __name__ == "__main__"` arranca el **servidor de desarrollo** de Flask. En producción la app se sirve con Gunicorn apuntando al objeto `app` del módulo `app`.
- **`requirements.txt`**: versiones fijadas para que la construcción sea reproducible.

---

## Variables de entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `REDIS_HOST` | `localhost` | Nombre de host o IP del servidor Redis. |
| `REDIS_PORT` | `6379` | Puerto de Redis. |
| `MENSAJE_BIENVENIDA` | `¡Hola desde Flask!` | Título que aparece en la página. Útil para comprobar que tus variables llegan al contenedor. |
| `PORT` | `5000` | Puerto del servidor de **desarrollo** (solo aplica al ejecutar `app.py` directamente). |

---

## Rutas

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Página HTML: suma una visita y muestra el total y la tabla por contenedor. |
| `GET` | `/api/visitas` | JSON con el total y el desglose por contenedor (no suma visitas). |
| `POST` | `/api/reiniciar` | Borra los contadores. |
| `GET` | `/health` | `200 {"estado":"ok"}` si Redis responde; `503` si no hay conexión. |

---

## Ejecución local sin Docker (referencia)

1. Necesitas Python y un servidor Redis corriendo en tu máquina.
2. Crea un entorno virtual e instala las dependencias de `requirements.txt`.
3. Ejecuta `app.py` con Python para usar el servidor de desarrollo, **o** usa Gunicorn indicando la dirección de escucha y el objeto WSGI (`módulo:variable`).

---

## Reto: dockerizar la aplicación

> Pistas, no soluciones. Apóyate en la documentación oficial.

### Parte 1: el `Dockerfile` de la aplicación web

1. **Imagen base:** usa la imagen oficial de Python con una versión explícita. Compara las variantes `slim` y `alpine` (tamaño y compatibilidad de paquetes).
2. **Variables de Python útiles en contenedores:** investiga `PYTHONDONTWRITEBYTECODE` y `PYTHONUNBUFFERED`. ¿Qué pasa con los logs si no usas la segunda?
3. **Caché de capas:** copia **primero** `requirements.txt`, instala dependencias y **después** copia el resto del código. Modifica `app.py` y vuelve a construir: la capa de instalación no debería repetirse.
4. **Instalación sin basura:** busca la opción del instalador de paquetes que evita guardar la caché de descargas dentro de la imagen.
5. **Usuario sin privilegios:** crea un usuario de sistema y cambia a él antes del comando final.
6. **Puerto:** documenta el puerto en el que escuchará Gunicorn.
7. **Comando de arranque:** usa Gunicorn, no el servidor de desarrollo. Debe escuchar en `0.0.0.0` (no en `127.0.0.1`). Investiga la opción para definir el número de *workers*.
8. **`.dockerignore`:** excluye entornos virtuales, cachés de Python (`__pycache__`), `.git`, etc.

### Parte 2: el `docker-compose.yml`

1. Define **dos servicios**: uno para la web (construido desde tu `Dockerfile`) y otro para Redis (imagen oficial, versión explícita).
2. En el servicio web, define `REDIS_HOST` con el **nombre del servicio** de Redis. Esa es la magia del DNS interno de Compose.
3. **No publiques** el puerto de Redis hacia tu máquina: solo la web necesita hablar con él. Publica únicamente el puerto de la web.
4. Haz que la web **dependa** de Redis. Investiga la diferencia entre "esperar a que el contenedor arranque" y "esperar a que esté sano" (`condition` dentro de `depends_on`).
5. Agrega un **healthcheck** a Redis usando su propia herramienta de línea de comandos.
6. Agrega un **volumen con nombre** para la carpeta de datos de Redis. Investiga en qué ruta guarda datos la imagen oficial y cómo activar la persistencia *append only*.
7. Cambia `MENSAJE_BIENVENIDA` desde Compose y comprueba el resultado.
8. **Escala** el servicio web a 3 réplicas. ¿Qué problema aparece con el mapeo de puertos? ¿Cómo lo resuelves? (pista: rangos de puertos, o un balanceador delante).

### Criterios de aceptación

- [ ] Al recargar la página el contador sube.
- [ ] Al reiniciar **todo** el entorno, el contador **conserva** su valor.
- [ ] Redis **no** es accesible desde tu máquina, solo desde la red de Compose.
- [ ] `/health` responde `200` con ambos servicios arriba, y `503` si detienes Redis.
- [ ] Modificar `app.py` y reconstruir **no** reinstala las dependencias.
- [ ] Con varias réplicas, la tabla "Visitas por contenedor" muestra varios nombres.

### Retos extra

- Agrega un servicio **Nginx** como balanceador delante de varias réplicas de la web.
- Crea un archivo `compose.override.yml` para desarrollo que monte el código como *bind mount* y use el servidor de desarrollo con recarga automática.
- Mueve las variables a un archivo `.env` y verifica cómo Compose las interpola.
- Agrega un *healthcheck* al servicio web usando la ruta `/health`.

---

## Errores comunes

| Síntoma | Causa probable |
|---|---|
| `Error 111 connecting to localhost:6379. Connection refused` | Falta `REDIS_HOST` o apunta a `localhost`. |
| La app responde en el contenedor pero no desde tu navegador | El servidor escucha en `127.0.0.1` en lugar de `0.0.0.0`. |
| No ves los logs de la app en tiempo real | Salida de Python con *buffer*; revisa `PYTHONUNBUFFERED`. |
| El contador vuelve a 0 tras recrear todo | Falta el volumen de Redis o la persistencia está desactivada. |
| `Bind for 0.0.0.0:XXXX failed: port is already allocated` al escalar | Varias réplicas intentan publicar el mismo puerto del host. |

---

## Referencias

- Imagen oficial de Python: <https://hub.docker.com/_/python>
- Imagen oficial de Redis: <https://hub.docker.com/_/redis>
- Guía de inicio de Docker Compose: <https://docs.docker.com/compose/gettingstarted/>
- Redes en Compose: <https://docs.docker.com/compose/how-tos/networking/>
- Orden de arranque (`depends_on`): <https://docs.docker.com/compose/how-tos/startup-order/>
- Despliegue de Flask con Gunicorn: <https://flask.palletsprojects.com/en/stable/deploying/gunicorn/>
