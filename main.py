from app.api.endpoints import router
from app.core.metrics import *

app = create_app()
app.include_router(router)

# Middleware for global request tracking
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Track request metrics
    APIMetrics.REQUEST_COUNTER.labels(
        method=request.method, 
        endpoint=request.url.path, 
        status=response.status_code
    ).inc()
    
    APIMetrics.RESPONSE_TIME.labels(
        method=request.method, 
        endpoint=request.url.path
    ).observe(process_time)
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)