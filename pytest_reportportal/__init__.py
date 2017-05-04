import logging

from .service import PyTestService


class RPlogHandler(logging.Handler):

    # Map loglevel codes from `logging` module to ReportPortal text names:
    _loglevel_map = {
        logging.NOTSET: "TRACE",
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "ERROR",
    }
    _sorted_levelnos = sorted(_loglevel_map.keys(), reverse=True)

    def __init__(self, level=logging.NOTSET):
        super(RPlogHandler, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

        for level in self._sorted_levelnos:
            if level <= record.levelno:
                break

        return PyTestService.post_log(msg, loglevel=self._loglevel_map[level])
