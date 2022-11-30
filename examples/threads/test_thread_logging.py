import logging
import threading

from reportportal_client.steps import step

log = logging.getLogger(__name__)


def worker():
    log.info("TEST_INFO")
    log.debug("TEST_DEBUG")


def test_log():
    t = threading.Thread(target=worker)
    log.info("TEST_BEFORE_THREADING")
    with step("Some nesting where the thread logs should go"):
        t.start()
    t.join()
