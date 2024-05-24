import logging
import os
import time
import logging

def get_logger(module_name=None):
    # Use the provided module name or default to 'root'
    logger = logging.getLogger(module_name)

    # Define the format for the logging messages
    log_format = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    
    # Set the logging level
    level = logging.INFO
    logger.setLevel(level)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt='%H:%M:%S'))
        logger.addHandler(console_handler)
        logger.propagate = False

    return logger



def exit_process(is_error=True, delayed=False):
    from threading import Thread
    import _thread
    status = 1 if is_error else 0
    Thread(target=lambda: (time.sleep(3), _thread.interrupt_main()), daemon=True).start()
    Thread(target=lambda: (time.sleep(6), os._exit(status)), daemon=True).start()
    if not delayed:
        import sys
        sys.exit(status)
