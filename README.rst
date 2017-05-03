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
    rp_uuid = uuid Report Portal
    rp_endpoint = http://ip:port
    rp_project = Project of Report Portal

Also launch tags could be added, but this parapmeter is not
mandatory :code:`rp_launch_tags = 'PyTest' 'Report_Portal'`.


Logging
~~~~~~~

For logging of the test item flow to Report Portal, please, use the python
logging handler privided by plugin like bellow:

.. code-block:: python

    # Import Report Portal handler in the test module.
    from pytest_reportportal import RPlogHandler
    # Get logger.
    logger = logging.getLogger()
    # Create hanler, set log level add it to the logger.
    rp_handler = RPlogHandler()
    rp_handler.setLevel(logging.INFO)
    logger.addHandler(rp_handler)
    # In this case only INFO messages will be sent to the Report Portal.
    def test_one(self):
        logger.info("Case1. Step1")
        x = "this"
        logger.info("Case1. Step2")
        assert 'h' in x


Launching
~~~~~~~~~

To run test with Report Portal you need to specify neme of :code:`launch`:

.. code-block:: bash

    py.test ./tests --rp-launch AnyLaunchName


Copyright Notice
----------------
Licensed under the [GPLv3](https://www.gnu.org/licenses/quick-guide-gplv3.html)
license (see the LICENSE file).
