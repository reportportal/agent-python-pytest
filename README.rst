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

- :code:`rp_uuid` - number could be found in the User profile section
- :code:`rp_project` - name of project in Report Potal
- :code:`rp_endpoint` - address of Report Portal Server

Example of :code:`pytest.ini`:

.. code-block:: text

    [pytest]
    rp_uuid = fb586627-32be-47dd-93c1-678873458a5f
    rp_endpoint = http://192.168.1.10:8080
    rp_project = user_personal
    rp_launch_tags = 'PyTest' 'Smoke'

Also launch tags could be added, but this parapmeter is not
mandatory :code:`rp_launch_tags = 'PyTest' 'Report_Portal'`.


Logging
~~~~~~~

For logging of the test item flow to Report Portal, please, use the python
logging handler privided by plugin like bellow:

.. code-block:: python

    import logging
    # Import Report Portal logger and handler to the test module.
    from pytest_reportportal import RPLogger, RPLogHandler
    # Setting up a logging.
    logging.setLoggerClass(RPLogger)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # Create handler for Report Portal.
    rp_handler = RPlogHandler()
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


Launching
~~~~~~~~~

To run test with Report Portal you need to specify neme of :code:`launch`:

.. code-block:: bash

    py.test ./tests --rp-launch AnyLaunchName


Copyright Notice
----------------

Licensed under the GPLv3_ license (see the LICENSE file).

.. _GPLv3:  https://www.gnu.org/licenses/quick-guide-gplv3.html
