# ReportPortal integration for pytest framework

Pytest plugin for reporting test results of the Pytest to the ReportPortal.

> **DISCLAIMER**: We use Google Analytics for sending anonymous usage information such as agent's and client's names,
> and their versions after a successful launch start. This information might help us to improve both ReportPortal
> backend and client sides. It is used by the ReportPortal team only and is not supposed for sharing with 3rd parties.

[![PyPI](https://img.shields.io/pypi/v/pytest-reportportal.svg?maxAge=259200)](https://pypi.python.org/pypi/pytest-reportportal)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-reportportal.svg)](https://pypi.org/project/pytest-reportportal)
[![Tests](https://github.com/reportportal/agent-python-pytest/actions/workflows/tests.yml/badge.svg)](https://github.com/reportportal/agent-python-pytest/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/reportportal/agent-python-pytest/graph/badge.svg?token=x5ZHqZKJFV)](https://codecov.io/gh/reportportal/agent-python-pytest)
[![Join Slack chat!](https://img.shields.io/badge/slack-join-brightgreen.svg)](https://slack.epmrpp.reportportal.io/)
[![stackoverflow](https://img.shields.io/badge/reportportal-stackoverflow-orange.svg?style=flat)](http://stackoverflow.com/questions/tagged/reportportal)
[![Build with Love](https://img.shields.io/badge/build%20with-❤%EF%B8%8F%E2%80%8D-lightgrey.svg)](http://reportportal.io?style=flat)

## Installation

To install pytest plugin execute next command in a terminal:

```bash
pip install pytest-reportportal
```

Look through the `CONTRIBUTING.rst` for contribution guidelines.

## Configuration

Prepare the config file `pytest.ini` in root directory of tests or specify any one using pytest command line option:

```bash
py.test -c config.cfg
```

The `pytest.ini` file should have next mandatory fields:

- `rp_api_key` - value could be found in the User Profile section
- `rp_project` - name of project in ReportPortal
- `rp_endpoint` - address of ReportPortal Server

Example of `pytest.ini`:

```text
[pytest]
rp_api_key = fb586627-32be-47dd-93c1-678873458a5f
rp_endpoint = http://192.168.1.10:8080
rp_project = user_personal
rp_launch = AnyLaunchName
rp_launch_attributes = 'PyTest' 'Smoke'
rp_launch_description = 'Smoke test'
rp_ignore_attributes = 'xfail' 'usefixture'
```

- The `rp_api_key` can also be set with the environment variable `RP_API_KEY`. This will override the value set for `rp_api_key` in pytest.ini

There are also optional parameters:
https://reportportal.io/docs/log-data-in-reportportal/test-framework-integration/Python/pytest/

## Examples

For logging of the test item flow to ReportPortal, please, use the python logging handler provided by plugin like
below:

in `conftest.py`:

```python
import logging

import pytest

from reportportal_client import RPLogger


@pytest.fixture(scope="session")
def rp_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.setLoggerClass(RPLogger)
    return logger
```

in tests:

```python
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
```

## Launching

To run test with ReportPortal you must provide `--reportportal` flag:

```bash
py.test ./tests --reportportal
```

Check the documentation to find more detailed information about how to integrate pytest with ReportPortal using the
agent:
https://reportportal.io/docs/log-data-in-reportportal/test-framework-integration/Python/pytest/

## Copyright Notice

Licensed under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license (see the LICENSE file).
