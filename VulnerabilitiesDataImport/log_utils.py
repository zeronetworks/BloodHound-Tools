import logging
import sys


logger = logging.getLogger(__name__)


def setup_logging(logging_level=logging.INFO):
    logger.setLevel(logging_level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging_level)

    console_formatter = logging.Formatter('%(message)s')
    if logging_level == logging.DEBUG:
        console_formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
