===================
agent-python-pytest
===================


**Important:** this is draft version under development.

Pytest plugin for reporting test results of Pytest to the 'Reportal Portal'.

Usage
-----

Installation
~~~~~~~~~~~~

To install pytest plugin execute next command in a terminal:

.. code-block:: bash

    pip install pytest-reportportal


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
    rp_launch_tags = 'PyTest' 'Smoke'
    rp_launch_description = 'Smoke test'

The following parapmeters are optional:

- :code:`rp_launch = AnyLaunchName` - launch name (could be overriden
  by pytest --rp-launch option, default value is 'Pytest Launch')
- :code:`rp_launch_tags = 'PyTest' 'Smoke'` - list of tags
- :code:`rp_launch_description = 'Smoke test'` - launch description
- :code:`rp_log_batch_size = 20` - size of batch log request


Examples
~~~~~~~~

For logging of the test item flow to Report Portal, please, use the python
logging handler provided by plugin like bellow:

.. code-block:: python

    import logging
    # Import Report Portal logger and handler to the test module.
    from pytest_reportportal import RPLogger, RPLogHandler
    # Setting up a logging.
    logging.setLoggerClass(RPLogger)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # Create handler for Report Portal.
    rp_handler = RPLogHandler()
    # Set INFO level for Report Portal handler.
    rp_handler.setLevel(logging.INFO)
    # Add handler to the logger.
    logger.addHandler(rp_handler)


    # In this case only INFO messages will be sent to the Report Portal.
    def test_one():
        logger.info("Case1. Step1")
        x = "this"
        logger.info("x is: %s", x)
        assert 'h' in x

        # Message with an attachment.
        import subprocess
        free_memory = subprocess.check_output("free -h".split())
        logger.info(
            "Case1. Memory consumption",
            attachment={
                "name": "free_memory.txt",
                "data": free_memory,
                "mime": "application/octet-stream",
            },
        )

        # This debug message will not be sent to the Report Portal.
        logger.debug("Case1. Debug message")

Plugin can report doc-strings of tests as :code:`descriptions`:

.. code-block:: python

    def test_one():
        """
        Description of the test case which will be sent to Report Portal
        """
        pass

Pytest markers will be attached as :code:`tags` to Report Portal items.
In the following example tags 'linux' and 'win32' will be used:

.. code-block:: python

    import pytest

    @pytest.mark.win32
    @pytest.mark.linux
    def test_one():
        pass


Launching
~~~~~~~~~

To run test with Report Portal you can specify name of :code:`launch`:

.. code-block:: bash

    py.test ./tests --rp-launch AnyLaunchName


Copyright Notice
----------------

Licensed under the GPLv3_ license (see the LICENSE file).

.. _GPLv3:  https://www.gnu.org/licenses/quick-guide-gplv3.html
