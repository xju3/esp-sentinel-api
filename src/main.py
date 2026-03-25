from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import settings
from .core.logging import setup_logging
from .services.mqtt_service import mqtt_service
from .api.routes import router

logger = setup_logging()

def create_application() -> FastAPI:
    app = FastAPI(
        title="Sentinel Server API",
        version="0.1.0",
        description="API for monitoring machine statuses via MQTT"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(router)
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting MQTT service...")
        mqtt_service.connect()
        
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Stopping MQTT service...")
        mqtt_service.disconnect()
        
    return app

app = create_application()