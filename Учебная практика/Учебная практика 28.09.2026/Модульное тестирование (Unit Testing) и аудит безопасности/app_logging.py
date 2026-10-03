import logging
from pathlib import Path


DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "app.log"
LOG_FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("partner_crm")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMATTER)
LOGGER.addHandler(console_handler)


def configure_logging(log_path: str | Path = DEFAULT_LOG_PATH) -> None:
    for handler in LOGGER.handlers[:]:
        handler.close()
        LOGGER.removeHandler(handler)
    try:
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    except OSError as error:
        handler = logging.StreamHandler()
        handler.setFormatter(LOG_FORMATTER)
        LOGGER.addHandler(handler)
        LOGGER.error("Не удалось открыть app.log; ошибки записываются в консоль: %s", error)
        return
    handler.setFormatter(LOG_FORMATTER)
    LOGGER.addHandler(handler)
