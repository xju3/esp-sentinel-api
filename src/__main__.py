import uvicorn
from .main import app
from .config.settings import settings


def main() -> None:
    """Run the ASGI application with settings from API_HOST/API_PORT."""
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()