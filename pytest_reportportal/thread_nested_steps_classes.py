class NestedStep:
    """
    This class contains information about a specific nested step
    """

    def __init__(self, name, id):
        self.name = name
        self.id = id


class ThreadNestedSteps:
    """
    A class which contains all the information on the nested steps which were created under a certain thread
    """

    def __init__(self, test_threads_nested_steps, thread, test_item_id):
        self.thread = thread
        self.nested_steps_stack = []
        self.test_item_id = test_item_id
        self.test_threads_nested_steps = test_threads_nested_steps
        self.nested_steps_info = {}

    @property
    def last_nested_step(self):
        """
        A property which returns the last nested step in the hierarchy that was created under the thread or None
        """
        return None if not self.nested_steps_stack else self.nested_steps_info[self.nested_steps_stack[-1]]

    def add_nested_step(self, step_id, step_name):
        """
        This method update the new created step under this instance
        :param step_id: The id of the nested step
        :param step_name: The name of the nested step
        :return:
        """
        self.nested_steps_stack.append(step_id)
        self.nested_steps_info[step_id] = NestedStep(name=step_name, id=step_id)

    def remove_nested_step(self, step_id=None):
        """
        This method removes a step from this instance
        :param step_id: The id of the nested step or None - if None is provided, then this method will remove the
                        last nested step
        """
        if not step_id:
            step_id = self.nested_steps_stack.pop()
        else:
            self.nested_steps_stack.remove(step_id)
        self.nested_steps_info.pop(step_id)


class TestThreadsNestedSteps:
    """
    This class manages all the threads that contain nested steps under a specific test
    This class was created in order to help the RP client to mix logs which were created under nested steps from
    different threads
    """

    def __init__(self):
        self._threads_nested_steps_dict = {}
        self.test_item_id = None
        self.nested_steps_exceptions = []

    def __getitem__(self, item):
        thread_nested_steps = self._threads_nested_steps_dict.get(item)
        if not thread_nested_steps:
            raise KeyError(f'No such thread with identifier {item} was found')
        return thread_nested_steps

    def get(self, thread_ident):
        """
        This method accepts a unique id of a thread and returns its ThreadSteps instance
        :param thread_ident: An id of a certain thread  - int
        :return: The ThreadNestedSteps instance which contains the information on the steps of the thread
        """
        return self._threads_nested_steps_dict.get(thread_ident)

    def add_thread(self, thread):
        """
        This method adds a new thread to the _threads_steps_dict in order to be able to save steps information about it
        :param thread: threading.Thread instance
        """
        self._threads_nested_steps_dict[thread.ident] = ThreadNestedSteps(self, thread, self.test_item_id)

    def set_current_test_item(self, test_item_id):
        """
        This method init all the relevant dicts and lists and updates the self.test_item_id with the new test item id
        :param test_item_id: The test item id - str
        :return:
        """
        self.test_item_id = test_item_id
        self._threads_nested_steps_dict.clear()
        self.nested_steps_exceptions.clear()

    def get_new_item_parent_id(self, thread):
        """
        This method returns the parent item id which the new item (either nested step or log entry) should be created
        under
        :param thread: threading.Thread instance
        :return: The parent item id - str
        """
        while thread:
            thread_nested_steps = self.get(thread.ident)
            if thread_nested_steps and thread_nested_steps.last_nested_step:
                return thread_nested_steps.last_nested_step.id
            thread = getattr(thread, 'parent', None)

        return self.test_item_id
