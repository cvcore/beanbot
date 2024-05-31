import logging
import os
from datetime import datetime

# Create a logger instance
logger = logging.getLogger(__name__)

# Set the logging level
logger.setLevel(logging.INFO)

# Create a file handler
log_file = f'logs/beanbot_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = logging.FileHandler(f'logs/beanbot_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log')

# Create a stream handler
stream_handler = logging.StreamHandler()

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


if __name__ == "__main__":
    # test the logger
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
    logger.critical('This is a critical message')
