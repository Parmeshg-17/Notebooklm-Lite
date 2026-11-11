import logging
import sys
from app.core.config import settings

def setup_logging() -> None:
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("notebooklm")

