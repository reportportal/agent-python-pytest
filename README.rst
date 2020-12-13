===================
agent-python-pytest
===================

Pytest plugin for reporting test results of Pytest to the Reportal Portal.

* Usage
* Installation
* Configuration
* Contribution
* Examples
* Launching
* Send attachement (screenshots)
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

**IMPORTANT!**
The latest version **does not** support Report Portal versions below 5.0.0.

Specify the last one release of the client version 1 to install or update the client for other versions of Report Portal below 5.0.0:

.. code-block:: bash

    pip install pytest-reportportal~=1.0


Contribution
~~~~~~~~~~~~~

All the fixes for the agent that supports Report Portal versions below 5.0.0 should go into the v1 branch.
The master branch will store the code base for the agent for Report Portal versions 5 and above.


Configuration
~~~~~~~~~~~~~

Prepare the config file :code:`pytest.ini` in root directory of tests or specify
any one using pytest command line option:

.. code-block:: bash

    py.test -c config.cfg


The :code:`pytest.ini` file should have next mandatory fields:

- :code:`rp_uuid` - value could be found in the User Profile section
- :code:`rp_project` - name of project in Report Potal
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
    rp_ignore_errors = True
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
- :code:`rp_ignore_errors = True` - Ignore Report Portal errors (exit otherwise)
- :code:`rp_ignore_attributes = 'xfail' 'usefixture'` - Ignore specified pytest markers
- :code:`rp_hierarchy_dirs = True` - Enables hierarchy for tests directories, default `False`. Doesn't support 'xdist' plugin.
- :code:`rp_hierarchy_module = True` - Enables hierarchy for module, default `True`. Doesn't support 'xdist' plugin.
- :code:`rp_hierarchy_class = True` - Enables hierarchy for class, default `True`. Doesn't support 'xdist' plugin.
- :code:`rp_hierarchy_parametrize = True` - Enables hierarchy parametrized tests, default `False`. Doesn't support 'xdist' plugin.
- :code:`rp_hierarchy_dirs_level = 0` - Directory starting hierarchy level (from pytest.ini level) (default `0`)
- :code:`rp_issue_marks = 'xfail' 'issue'` - Pytest marks that could be used to get issue information (id, type, reason)
- :code:`rp_issue_system_url = http://bugzilla.some.com/show_bug.cgi?id={%issue_id}` - issue URL (issue_id will be filled by parameter from pytest mark)
- :code:`rp_issue_id_marks = True` - Enables adding marks for issue ids (e.g. "issue:123456")
- :code:`rp_verify_ssl = True` - Verify SSL when connecting to the server
- :code:`rp_display_suite_test_file = True` In case of True, include the suite's relative file path in the launch name as a convention of "<RELATIVE_FILE_PATH>::<SUITE_NAME>". In case of False, set the launch name to be the suite name only - this flag is relevant only when "rp_hierarchy_module" flag is set to False


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

    from pytest_reportportal import RPLogger, RPLogHandler


    @pytest.fixture(scope="session")
    def rp_logger(request):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        # Create handler for Report Portal if the service has been
        # configured and started.
        if hasattr(request.node.config, 'py_test_service'):
            # Import Report Portal logger and handler to the test module.
            logging.setLoggerClass(RPLogger)
            rp_handler = RPLogHandler(request.node.config.py_test_service)
            # Add additional handlers if it is necessary
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            logger.addHandler(console_handler)
        else:
            rp_handler = logging.StreamHandler(sys.stdout)
        # Set INFO level for Report Portal handler.
        rp_handler.setLevel(logging.INFO)
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
~~~~~~~~~

Some pytest marks could be used to specify information about skipped or failed test result.
List of this marks should be specified in pytest ini file (see :code:`rp_issue_marks`).

The following mark fields are used to get information about test issue:

- :code:`issue_id` - issue id (or list) in tracking system. This id will be added as comment to test fail result. If URL is specified in pytest ini file (see :code:`rp_issue_system_url`), id will added as link to tracking system.
- :code:`reason` - some comment that will be added to test fail description.
- :code:`issue_type` - short name of RP issue type that should be assigned to failed or skipped test.

Example:

.. code-block:: python

    @pytest.mark.issue(issue_id="111111", reason="Some bug", issue_type="PB")
    def test():
        assert False


Send attachement (screenshots)
----------------

https://github.com/reportportal/client-Python#send-attachement-screenshots



Troubleshooting
~~~~~~~~~

In case you have connectivity issues (or similar problems) with Report Portal,
it's possible to ignore exceptions raised by :code:`pytest_reportportal` plugin.
For this, please, add following option to :code:`pytest.ini` configuration file.

.. code-block:: text

    [pytest]
    ...
    rp_ignore_errors = True

With option above all exceptions raised by Report Portal will be printed out to
`stderr` without causing test failures.

If you would like to temporary disable integrations with Report Portal just
deactivate :code:`pytest_reportportal` plugin with command like:

.. code-block:: bash

    py.test -p no:pytest_reportportal ./tests


Integration with GA
-------------------
ReportPortal is now supporting integrations with more than 15 test frameworks simultaneously. In order to define the most popular agents and plan the team workload accordingly, we are using Google analytics.

ReportPortal collects information about agent name and its version only. This information is sent to Google analytics on the launch start. Please help us to make our work effective.
If you still want to switch Off Google analytics, please change env variable the way below.

.. code-block:: bash

    export ALLURE_NO_ANALYTICS=1


Copyright Notice
----------------
..  Copyright Notice:  https://github.com/reportportal/agent-python-pytest#copyright-notice

Licensed under the `Apache 2.0`_ license (see the LICENSE file).

.. _Apache 2.0:  https://www.apache.org/licenses/LICENSE-2.0

