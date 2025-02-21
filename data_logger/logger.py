"""A python class which wraps the logging module to make testing easier."""

import logging

class wrapped_logging:
    def __init__(self, debug: bool) -> None:
        """Initialises the logger.
        Args:
            debug (bool): Whether to output debug logs.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        if debug:
            logging.basicConfig(filename="debug.log", filemode="w")

    def log_info(self, message: str) -> None:
        """Logs an info message to the logger.
        Args:
            message (str): The message to log.
        """
        self.logger.info(message)

    def log_error(self, message: str) -> None:
        """Logs an error message to the logger.
        Args:
            message (str): The message to log.
        """
        self.logger.error(message)

    def log_warning(self, message: str) -> None:
        """Logs a warning message to the logger.
        Args:
            message (str): The message to log.
        """
        self.logger.warning(message)