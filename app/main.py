import os
import signal
import sys
import time
import logging
from flask import Flask, jsonify, request
import redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['endpoint']
)

REDIS_HOST = os.environ.get('REDIS_HOST', 'redis-service')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')

redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            redis_client.ping()
            logger.info(f"Conectado a Redis en {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis no disponible: {e}")
            redis_client = None
    return redis_client

# ── SIGTERM Handler (graceful shutdown) ──────────────────────
is_shutting_down = False

def graceful_shutdown(signum, frame):
    global is_shutting_down
    logger.info(f"Señal {signum} recibida. Iniciando apagado controlado...")
    is_shutting_down = True
    time.sleep(5)
    logger.info("Apagado completado.")
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

@app.before_request
def check_shutdown():
    if is_shutting_down:
        return jsonify({"error": "Service shutting down"}), 503

# ── Endpoints ─────────────────────────────────────────────────
@app.route('/health/live', methods=['GET'])
def liveness():
    return jsonify({"status": "alive"}), 200


@app.route('/health/ready', methods=['GET'])
def readiness():
    r = get_redis()
    if r is None:
        return jsonify({"status": "not ready", "reason": "Redis unavailable"}), 503
    try:
        r.ping()
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "reason": str(e)}), 503


@app.route('/', methods=['GET'])
def index():
    REQUEST_COUNT.labels(method='GET', endpoint='/', status=200).inc()
    return jsonify({
        "service": "DevOps Final Project API",
        "version": os.environ.get('APP_VERSION', '1.0.0'),
        "environment": os.environ.get('APP_ENV', 'production')
    })


@app.route('/counter', methods=['GET', 'POST'])
def counter():
    r = get_redis()
    if r is None:
        return jsonify({"error": "Redis unavailable"}), 503
    if request.method == 'POST':
        value = r.incr('visit_counter')
        action = 'incremented'
    else:
        value = r.get('visit_counter') or 0
        action = 'retrieved'
    REQUEST_COUNT.labels(method=request.method, endpoint='/counter', status=200).inc()
    return jsonify({"action": action, "counter": int(value)})


@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
