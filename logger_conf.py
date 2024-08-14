import os
import sys
import logging
from datetime import datetime
from PyQt6.QtWidgets import QTextEdit


def init_logger():
    logger = logging.getLogger("logger")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    
    # File-Handler
    exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
    log_file_name = os.path.join(os.path.dirname(exe_path), 'logs', f'log_{datetime.now().strftime("%Y%m%d")}.log')
    os.makedirs(os.path.dirname(log_file_name), exist_ok=True)
    file_handler = logging.FileHandler(log_file_name,encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

class QTextEditHandler(logging.Handler):
    def __init__(self, parent: QTextEdit):
        super().__init__()
        self.text_edit = parent
        self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
 
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        self.text_edit.ensureCursorVisible()
 
    def format(self, record):
        if record.levelno == logging.DEBUG:
            color = 'gray'
        elif record.levelno == logging.INFO:
            color = 'black'
        elif record.levelno == logging.WARNING:
            color = 'orange'
        elif record.levelno == logging.ERROR:
            color = 'darkRed'
        elif record.levelno == logging.CRITICAL or record.levelno == logging.FATAL:
            color = 'red'
        else:
            color = 'blue'
        new_msg = self.formatter.format(record)
        msg = '<span style="color:{}">{}</span>'.format(color, new_msg)
        return msg