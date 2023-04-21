===================
agent-python-pytest
===================

.. image:: https://img.shields.io/pypi/v/pytest-reportportal.svg
    :target: https://pypi.python.org/pypi/pytest-reportportal
    :alt: Latest Version
.. image:: https://img.shields.io/pypi/pyversions/pytest-reportportal.svg
    :target: https://pypi.org/project/pytest-reportportal
    :alt: Supported python versions
.. image:: https://github.com/reportportal/agent-python-pytest/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/reportportal/agent-python-pytest/actions/workflows/tests.yml
    :alt: Test status
.. image:: https://codecov.io/gh/reportportal/agent-python-pytest/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/reportportal/agent-python-pytest
    :alt: Test coverage
.. image:: https://slack.epmrpp.reportportal.io/badge.svg
    :target: https://slack.epmrpp.reportportal.io/
    :alt: Join Slack chat!


Pytest plugin for reporting test results of the Pytest to the Report Portal.

* Usage
* Installation
* Configuration
* Examples
* Launching
* Send attachment (screenshots)
* Troubleshooting
* Integration with GA
* Copyright Notice

Usage
-----

Installation
~~~~~~~~~~~~

To install pytest plugin execute next command in a terminal:

.. code-block:: bash

    pip install pytest-reportportal



Look through the CONTRIBUTING.rst for contribution guidelines.

Configuration
~~~~~~~~~~~~~

Prepare the config file :code:`pytest.ini` in root directory of tests or specify
any one using pytest command line option:

.. code-block:: bash

    py.test -c config.cfg


The :code:`pytest.ini` file should have next mandatory fields:

- :code:`rp_uuid` - value could be found in the User Profile section
- :code:`rp_project` - name of project in Report Portal
- :code:`rp_endpoint` - address of Report Portal Server

Example of :code:`pytest.ini`:

.. code-block:: text

    [pytest]
    rp_uuid = fb586627-32be-47dd-93c1-678873458a5f
    rp_endpoint = http://192.168.1.10:8080
    rp_project = user_personal
    rp_launch = AnyLaunchName
    rp_launch_attributes = 'PyTest' 'Smoke'
    rp_launch_description = 'Smoke test'
    rp_ignore_attributes = 'xfail' 'usefixture'

- The :code:`rp_uuid` can also be set with the environment variable `RP_UUID`. This will override the value set for :code:`rp_uuid` in pytest.ini

The following parameters are optional:

- :code:`rp_launch = AnyLaunchName` - launch name (could be overridden
  by pytest --rp-launch option, default value is 'Pytest Launch')
- :code:`rp_launch_id = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` - id of the existing launch (the session will not handle the lifecycle of the given launch)
- :code:`rp_launch_attributes = 'PyTest' 'Smoke' 'Env:Python3'` - list of attributes for launch
- :code:`rp_parent_item_id = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` - id of the existing test item for session to use as parent item for the tests (the session will not handle the lifecycle of the given test item)
- :code:`rp_tests_attributes = 'PyTest' 'Smoke'` - list of attributes that will be added for each item in the launch
- :code:`rp_launch_description = 'Smoke test'` - launch description (could be overridden
  by pytest --rp-launch-description option, default value is '')

- :code:`rp_log_batch_size = 20` - size of batch log request
- :code:`rp_log_batch_payload_size = 65000000` - maximum payload size in bytes of async batch log requests
- :code:`rp_log_level = INFO` - The log level that will be reported
- :code:`rp_log_format = [%(levelname)7s] (%(name)s) %(message)s (%(filename)s:%(lineno)s)` - Format string to be used for logs sent to the service.
- :code:`rp_ignore_attributes = 'xfail' 'usefixture'` - Ignore specified pytest markers
- :code:`rp_is_skipped_an_issue = False` - Treat skipped tests as required investigation. Default is True.
- :code:`rp_hierarchy_dirs_level = 0` - Directory starting hierarchy level (from pytest.ini level) (default `0`)
- :code:`rp_hierarchy_dirs = True` - Enables hierarchy for tests directories, default `False`. Doesn't support 'xdist' plugin.
- :code:`rp_hierarchy_dir_path_separator` - Path separator to display directories in test hierarchy. In case of empty value current system path separator will be used (os.path.sep)
- :code:`rp_hierarchy_code` - Enables hierarchy for inner classes and parametrized tests, default `False`. Doesn't support 'xdist' plugin.
- :code:`rp_issue_system_url = https://bugzilla.some.com/show_bug.cgi?id={issue_id}` - issue URL (issue_id will be filled by parameter from pytest mark)
- :code:`rp_issue_id_marks = True` - Enables adding marks for issue ids (e.g. "issue:123456")
- :code:`rp_verify_ssl = True` - Verify SSL when connecting to the server
- :code:`rp_mode = DEFAULT` - DEBUG or DEFAULT launch mode. DEBUG launches are displayed in a separate tab and not visible to anyone except owner
- :code:`rp_thread_logging` - EXPERIMENTAL - Enables support for reporting logs from threads by patching the builtin Thread class. Use with caution.
- :code:`rp_launch_timeout = 86400` - Maximum time to wait for child processes finish, default value: 86400 seconds (1 day)



If you like to override the above parameters from command line, or from CI environment based on your build, then pass
- :code:`-o "rp_launch_attributes=Smoke Tests"` during invocation.

Examples
~~~~~~~~

For logging of the test item flow to Report Portal, please, use the python
logging handler provided by plugin like bellow:
in conftest.py:

.. code-block:: python

    import logging
    import sys

    import pytest

    from reportportal_client import RPLogger


    @pytest.fixture(scope="session")
    def rp_logger():
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logging.setLoggerClass(RPLogger)
        return logger

in tests:

.. code-block:: python

    # In this case only INFO messages will be sent to the Report Portal.
    def test_one(rp_logger):
        rp_logger.info("Case1. Step1")
        x = "this"
        rp_logger.info("x is: %s", x)
        assert 'h' in x

        # Message with an attachment.
        import subprocess
        free_memory = subprocess.check_output("free -h".split())
        rp_logger.info(
            "Case1. Memory consumption",
            attachment={
                "name": "free_memory.txt",
                "data": free_memory,
                "mime": "application/octet-stream",
            },
        )

        # This debug message will not be sent to the Report Portal.
        rp_logger.debug("Case1. Debug message")

Plugin can report doc-strings of tests as :code:`descriptions`:

.. code-block:: python

    def test_one():
        """
        Description of the test case which will be sent to Report Portal
        """
        pass

Pytest markers will be attached as :code:`attributes` to Report Portal items.
In the following example attributes 'linux' and 'win32' will be used:

.. code-block:: python

    import pytest

    @pytest.mark.win32
    @pytest.mark.linux
    def test_one():
        pass

If you don't want to attach specific markers, list them in :code:`rp_ignore_attributes` parameter


Launching
~~~~~~~~~

To run test with Report Portal you must provide '--reportportal' flag:

.. code-block:: bash

    py.test ./tests --reportportal


Test issue info
~~~~~~~~~~~~~~~

Some pytest marks could be used to specify information about skipped or failed test result.

The following mark fields are used to get information about test issue:

- :code:`issue_id` - issue id (or list) in tracking system. This id will be added as comment to test fail result. If URL is specified in pytest ini file (see :code:`rp_issue_system_url`), id will added as link to tracking system.
- :code:`reason` - some comment that will be added to test fail description.
- :code:`issue_type` - short name of RP issue type that should be assigned to failed or skipped test.

Example:

.. code-block:: python

    @pytest.mark.issue(issue_id="111111", reason="Some bug", issue_type="PB")
    def test():
        assert False


Send attachment (screenshots)
------------------------------

https://github.com/reportportal/client-Python#send-attachment-screenshots

Test internal steps, aka "Nested steps"
---------------------------------------

To implement Nested steps reporting please follow our guide: https://github.com/reportportal/client-Python/wiki/Nested-steps

Also there are examples of usage:

* https://github.com/reportportal/examples-python/blob/master/pytest/tests/test_nested_steps.py
* https://github.com/reportportal/examples-python/blob/master/pytest/tests/test_nested_steps_ui.py

Troubleshooting
~~~~~~~~~~~~~~~
If you would like to temporary disable integrations with Report Portal just
deactivate :code:`pytest_reportportal` plugin with command like:

.. code-block:: bash

    py.test -p no:pytest_reportportal ./tests


Integration with Google analytics
---------------------------------
ReportPortal is now supporting integrations with more than 15 test frameworks simultaneously. In order to define the most popular agents and plan the team workload accordingly, we are using Google analytics.

ReportPortal collects information about agent name and its version only. This information is sent to Google Analytics on the launch start. Please help us to make our work effective.
If you still want to switch Off Google analytics, please change env variable the way below.

.. code-block:: bash

    export AGENT_NO_ANALYTICS=1


Copyright Notice
----------------
..  Copyright Notice:  https://github.com/reportportal/agent-python-pytest#copyright-notice

Licensed under the `Apache 2.0`_ license (see the LICENSE file).

.. _Apache 2.0:  https://www.apache.org/licenses/LICENSE-2.0
