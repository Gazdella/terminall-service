from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from config import settings
from dao.database import init_db_pool, close_db_pool
from routes import order_routes, callback_routes, session_routes
from services.rabbitmq_publisher import rmq_publisher

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.info("Starting Terminal Service...")
    await init_db_pool()
    await rmq_publisher.connect()
    yield
    LOGGER.info("Shutting down Terminal Service...")
    await rmq_publisher.close()
    await close_db_pool()

app = FastAPI(
    title="Terminal Service",
    description="Backend microservice for Z80 payment terminals",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_routes.router)
app.include_router(order_routes.router)
app.include_router(callback_routes.router)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "terminal-service",
        "keepz_configured": bool(settings.keepz_integrator_id)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.api_host, port=settings.api_port, reload=True)
