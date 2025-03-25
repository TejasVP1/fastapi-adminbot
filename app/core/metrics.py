from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
from prometheus_client import Counter, Histogram
import time
import traceback

# Custom metrics for detailed monitoring
class APIMetrics:
    """Centralized class for managing API metrics"""
    
    # Request counter for different endpoints
    REQUEST_COUNTER = Counter(
        'api_requests_total', 
        'Total number of API requests', 
        ['method', 'endpoint', 'status']
    )
    
    # Response time histogram for performance tracking
    RESPONSE_TIME = Histogram(
        'api_response_time_seconds', 
        'Response time of API endpoints', 
        ['method', 'endpoint']
    )
    
    # Error counter for tracking failures
    ERROR_COUNTER = Counter(
        'api_errors_total', 
        'Total number of API errors', 
        ['method', 'endpoint', 'error_type']
    )
    
    # Detailed method execution time tracking
    METHOD_EXECUTION_TIME = Histogram(
        'method_execution_time_seconds', 
        'Execution time of specific methods', 
        ['method_name']
    )

def create_app():
    """Create and configure FastAPI application with monitoring"""
    app = FastAPI(title="Loan Chatbot API")
    
    # CORS Configuration
    origins = [
        "http://localhost:5174", 
        "http://localhost:5173"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"], 
        allow_headers=["*"],
    )
    
    # Prometheus Middleware
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", handle_metrics)
    
    return app

def track_method_performance(method_name):
    """
    Decorator to track method execution time
    
    Usage:
    @track_method_performance('generate_sql')
    def generate_sql(...):
        # method implementation
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record method execution time
                APIMetrics.METHOD_EXECUTION_TIME.labels(
                    method_name=method_name
                ).observe(execution_time)
                
                return result
            except Exception as e:
                # Record error
                APIMetrics.ERROR_COUNTER.labels(
                    method=func.__name__, 
                    endpoint=method_name, 
                    error_type=type(e).__name__
                ).inc()
                raise
        return wrapper
    return decorator