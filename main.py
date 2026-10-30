import os
import socket
from flask import Flask, jsonify, request
import redis

app = Flask(__name__)

# --- Configuration (viendra du ConfigMap / Secret dans Kubernetes) ---
APP_NAME = os.environ.get("APP_NAME", "k8s-portfolio-app")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

# --- Connexion Redis ---
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=3,
)


@app.route("/")
def home():
    return jsonify({
        "app": APP_NAME,
        "message": "API Flask connectée à Redis",
        "pod_hostname": socket.gethostname(),
    })


@app.route("/healthz")
def healthz():
    """Utilisé pour les probes Kubernetes (liveness/readiness)."""
    try:
        r.ping()
        return jsonify({"status": "ok"}), 200
    except redis.exceptions.RedisError:
        return jsonify({"status": "redis unreachable"}), 503


@app.route("/count", methods=["GET"])
def get_count():
    """Retourne le nombre de visites enregistrées."""
    count = r.get("visits") or 0
    return jsonify({"visits": int(count)})


@app.route("/count", methods=["POST"])
def increment_count():
    """Incrémente le compteur de visites dans Redis."""
    new_count = r.incr("visits")
    return jsonify({"visits": new_count, "served_by": socket.gethostname()})


@app.route("/items", methods=["GET"])
def list_items():
    """Exemple de mini API CRUD : liste des items stockés dans Redis."""
    items = r.lrange("items", 0, -1)
    return jsonify({"items": items})


@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json(silent=True) or {}
    item = data.get("item")
    if not item:
        return jsonify({"error": "champ 'item' requis"}), 400
    r.rpush("items", item)
    return jsonify({"added": item}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=(LOG_LEVEL == "debug"))