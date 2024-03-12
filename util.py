import logging
import os
import time

class dotdict(dict):
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError as e:
            raise AttributeError(e)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    # __hasattr__ = dict.__contains__


import logging

def get_logger(module_name=None):
    # Use the provided module name or default to 'root'
    logger = logging.getLogger(module_name)

    # Define the format for the logging messages
    log_format = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    
    # Set the logging level
    level = logging.INFO
    logger.setLevel(level)

    # Check if the logger already has handlers to avoid duplicate logs
    if not logger.handlers:
        # Create a console handler with the specified format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt='%H:%M:%S'))
        
        # Add the console handler to the logger
        logger.addHandler(console_handler)

        # Avoid duplicate log entries in parent loggers
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

if __name__ == "__main__":
    pass
