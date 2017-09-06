import sys
import logging

from .service import PyTestService


class RPLogger(logging.getLoggerClass()):

    def __init__(self, name, level=0):
        super(RPLogger, self).__init__(name, level=level)

    def _log(self, level, msg, args, exc_info=None, extra=None,
             attachment=None):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        if logging._srcfile:
            # IronPython doesn't track Python frames, so findCaller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func = self.findCaller()
            except ValueError:
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else:
            fn, lno, func = "(unknown file)", 0, "(unknown function)"

        if exc_info and not isinstance(exc_info, tuple):
            exc_info = sys.exc_info()

        record = self.makeRecord(
            self.name, level, fn, lno, msg, args, exc_info, func, extra
        )
        record.attachment = attachment
        self.handle(record)


class RPLogHandler(logging.Handler):

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
        super(RPLogHandler, self).__init__(level)

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

        return PyTestService.post_log(
            msg,
            loglevel=self._loglevel_map[level],
            attachment=record.__dict__.get("attachment", None),
        )
