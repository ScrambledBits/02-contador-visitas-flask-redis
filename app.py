import os
import socket

import redis
from flask import Flask, jsonify, render_template

app = Flask(__name__)

cache = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
)

MENSAJE = os.environ.get("MENSAJE_BIENVENIDA", "¡Hola desde Flask!")
CLAVE_TOTAL = "visitas:total"
CLAVE_POR_HOST = "visitas:por_contenedor"


def registrar_visita():
    nombre_host = socket.gethostname()
    with cache.pipeline() as pipe:
        pipe.incr(CLAVE_TOTAL)
        pipe.hincrby(CLAVE_POR_HOST, nombre_host, 1)
        total, _ = pipe.execute()
    return total, nombre_host


@app.route("/")
def inicio():
    total, nombre_host = registrar_visita()
    return render_template(
        "index.html",
        mensaje=MENSAJE,
        total=total,
        host=nombre_host,
        por_host=cache.hgetall(CLAVE_POR_HOST),
    )


@app.route("/api/visitas")
def api_visitas():
    return jsonify(
        total=int(cache.get(CLAVE_TOTAL) or 0),
        por_contenedor={k: int(v) for k, v in cache.hgetall(CLAVE_POR_HOST).items()},
    )


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    cache.delete(CLAVE_TOTAL, CLAVE_POR_HOST)
    return jsonify(total=0)


@app.route("/health")
def health():
    try:
        cache.ping()
    except redis.exceptions.ConnectionError:
        return jsonify(estado="error", redis="sin conexion"), 503
    return jsonify(estado="ok", redis="conectado")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
