import logging

def setup_logging():
    """Basic logging configuration for the API."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)

logger = setup_logging()