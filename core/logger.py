import logging
import os
from PySide6.QtCore import QObject, Signal

class Signaller(QObject):
    log_signal = Signal(str)

class QListWidgetLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.signaller = Signaller()

    def emit(self, record):
        log_entry = self.format(record)
        self.signaller.log_signal.emit(log_entry)

def setup_logger(root_path):
    log_dir = os.path.join(root_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    
    logger = logging.getLogger("PhotoAlbumLogger")
    logger.setLevel(logging.INFO)
    
    # Previene duplicazioni di handler
    if logger.hasHandlers():
        logger.handlers.clear()
        
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    
    # File Handler (modalità 'w' cancella i vecchi log)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # GUI Handler
    gui_handler = QListWidgetLogHandler()
    gui_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(gui_handler)
    
    logger.info("=========================================")
    logger.info("PhotoAlbum Orderer - Avvio Sessione Log")
    logger.info("=========================================")
    
    return logger

def get_logger():
    return logging.getLogger("PhotoAlbumLogger")
