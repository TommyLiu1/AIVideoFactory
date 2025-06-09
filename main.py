
import uvicorn
from loguru import logger
from config import config
if __name__ == "__main__":
    logger.info(
        "start server, docs: http://127.0.0.1:" + str(config.listen_port) + "/docs"
    )
    uvicorn.run(
        app="asgi:app",
        host=config.listen_host,
        port=config.listen_port,
        reload=False,
        log_level="warning",
    )

