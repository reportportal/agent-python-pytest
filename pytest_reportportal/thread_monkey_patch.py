import threading


def set_new_thread_init_method():
    """
    Override the existing init method of the threading.Thread class in order for it to have the self.parent attribute
    """
    old_init = threading.Thread.__init__

    def new_thread_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self.parent = threading.current_thread()

    threading.Thread.__init__ = new_thread_init


def set_new_thread_run_method(rp_client):
    """
    This function overrides the run method of each thread in order to call to the _log_batch
    method of the rp_client so the remaining logs of the thread will be uploaded since now threads can be running under
    nested steps or open new nested steps
    :param rp_client: The report portal client instance
    """
    original_run_method =  threading.Thread.run

    def new_run_method(self):
        try:
            original_run_method(self)
        finally:
            rp_client._log_batch(None, force=True)

    threading.Thread.run = new_run_method
