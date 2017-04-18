import logging
from .service import PyTestService


class RPlogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(RPlogHandler, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

        return PyTestService.post_log(msg, log_level=self.level)
