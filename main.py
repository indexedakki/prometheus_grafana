from fastapi import FastAPI, Request, HTTPException
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
from fastapi.responses import Response
from prometheus_fastapi_instrumentator import Instrumentator
import logging

# Configure logging
logger = logging.getLogger("fastapi")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

app = FastAPI()

Instrumentator().instrument(app).expose(app)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Duration',
    ['method', 'endpoint']
)

# CPU and RAM usage metrics
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU Usage Percentage')
RAM_USAGE = Gauge('ram_usage_percent', 'RAM Usage Percentage')

# Middleware to track requests
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    method = request.method
    endpoint = request.url.path
    start_time = time.time()
    
    response = await call_next(request)
    status_code = response.status_code
    
    # Record metrics
    REQUEST_COUNT.labels(method, endpoint, status_code).inc()
    REQUEST_DURATION.labels(method, endpoint).observe(time.time() - start_time)
    
    return response

# Task to update CPU and RAM usage metrics
def update_system_metrics():
    CPU_USAGE.set(psutil.cpu_percent(interval=1))
    RAM_USAGE.set(psutil.virtual_memory().percent)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    # logger.info("Updating system metrics")
    # update_system_metrics()
    # logger.info("Updated system metrics")
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )

@app.get("/heavy-operation")
async def heavy_operation():
    try:
        # Simulating a heavy operation: large matrix multiplication
        size = 1000
        matrix_a = np.random.rand(size, size)
        matrix_b = np.random.rand(size, size)
        result = np.dot(matrix_a, matrix_b)
        
        # Simulate a failure condition
        if np.random.rand() > 0.95:  # 5% chance of failure
            raise ValueError("Simulated heavy operation failure")

        return {"message": "Success", "result_sum": np.sum(result)}
    except Exception as e:
        # Increment the failure counter when an exception occurs
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Example endpoint
@app.get("/")
async def root():

    return {"message": "Hello World"}