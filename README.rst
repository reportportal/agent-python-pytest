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
.. image:: https://codecov.io/gh/reportportal/agent-python-pytest/branch/develop/graph/badge.svg
    :target: https://codecov.io/gh/reportportal/agent-python-pytest
    :alt: Test coverage
.. image:: https://slack.epmrpp.reportportal.io/badge.svg
    :target: https://slack.epmrpp.reportportal.io/
    :alt: Join Slack chat!


Pytest plugin for reporting test results of the Pytest to the ReportPortal.

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

- :code:`rp_api_key` - value could be found in the User Profile section
- :code:`rp_project` - name of project in ReportPortal
- :code:`rp_endpoint` - address of ReportPortal Server

Example of :code:`pytest.ini`:

.. code-block:: text

    [pytest]
    rp_api_key = fb586627-32be-47dd-93c1-678873458a5f
    rp_endpoint = http://192.168.1.10:8080
    rp_project = user_personal
    rp_launch = AnyLaunchName
    rp_launch_attributes = 'PyTest' 'Smoke'
    rp_launch_description = 'Smoke test'
    rp_ignore_attributes = 'xfail' 'usefixture'

- The :code:`rp_api_key` can also be set with the environment variable `RP_API_KEY`. This will override the value set for :code:`rp_api_key` in pytest.ini

There are also optional parameters:
https://reportportal.io/docs/log-data-in-reportportal/test-framework-integration/Python/pytest/

Examples
~~~~~~~~

For logging of the test item flow to ReportPortal, please, use the python
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

    # In this case only INFO messages will be sent to the ReportPortal.
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

        # This debug message will not be sent to the ReportPortal.
        rp_logger.debug("Case1. Debug message")

Launching
~~~~~~~~~

To run test with ReportPortal you must provide '--reportportal' flag:

.. code-block:: bash

    py.test ./tests --reportportal

Check the documentation to find more detailed information about how to integrate pytest with ReportPortal using an agent:
https://reportportal.io/docs/log-data-in-reportportal/test-framework-integration/Python/pytest/

Copyright Notice
----------------
..  Copyright Notice:  https://github.com/reportportal/agent-python-pytest#copyright-notice

Licensed under the `Apache 2.0`_ license (see the LICENSE file).

.. _Apache 2.0:  https://www.apache.org/licenses/LICENSE-2.0
