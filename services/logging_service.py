import logging
from logging.handlers import RotatingFileHandler


# A Singleton metaclass that creates and shares a single instance of a class.
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class LoggingService(metaclass=SingletonMeta):
    def __init__(self, log_file='app.log', level=logging.INFO, max_bytes=10000, backup_count=5):
        if not hasattr(self, 'is_initialized'):
            self.log_file = log_file
            self.level = level
            self.max_bytes = max_bytes
            self.backup_count = backup_count
            self.setup_logging()
            self.is_initialized = True
    
    def setup_logging(self):
        # Sets up the logging configuration
        logging.basicConfig(
            level=self.level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=self.log_file,
            filemode='w'
        )
        
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        
        logging.getLogger('').addHandler(handler)

    def log(self, level, message):
        # Logs a message at the specified level
        logger = logging.getLogger(__name__)
        if level == 'debug':
            logger.debug(message)
        elif level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
        elif level == 'critical':
            logger.critical(message)
        else:
            logger.info(message)
