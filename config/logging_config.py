import logging
import config.config
import sys

# create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(process)d %(filename)s(%(lineno)d) %(message)s')

if config.config.LOG_IN_FILE:
    # create file handler
    if 'unittest' in sys.modules:
        fh = logging.FileHandler(config.config.LOG_TEST_PATH)
    else:
        fh = logging.FileHandler(config.config.LOG_PATH)

    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

if config.config.LOG_IN_CONSOLE:
    # create stream handler (logging in the console)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
