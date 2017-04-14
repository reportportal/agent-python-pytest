import logging
from service import PyTestService


class RPlogHandler(logging.Handler):
    def __init__(self, level="INFO"):

        super(RPlogHandler, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

        print("LOGLEVEL in RPlogHandler %s" % self.level)
        PyTestService.post_log(msg, log_level=self.level)


def getLogger(name='RP_Logger', loglevel='INFO'):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    # if logger 'name' does not already exist, create it and attach handlers
    else:
        # set logLevel to loglevel or to INFO if requested level is incorrect
        # loglevel = getattr(logging, loglevel.upper(), logging.INFO)
        logger.setLevel(loglevel)
        handler = RPlogHandler(loglevel)
        logger.addHandler(handler)

    return logger
