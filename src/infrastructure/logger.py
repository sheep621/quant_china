import logging
import sys
import os
from pathlib import Path

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Setup a logger with console and optional file output
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Check if handlers already exist to avoid duplicates
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def get_system_logger():
    """Get the default system logger configured by config/system_config.yaml"""
    # Simple default for now, can be upgraded to read config
    return setup_logger('quant_system', log_file='logs/quant.log')
