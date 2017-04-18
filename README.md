# agent-python-pytest
Plugin for test item reporting to Report Portal server

## Description:
Plugin for reporting items results of Pytest to the 'Reportal Portal'.
```bash
pip install pytest-reportportal
```
## Usage:

### Prepare the config file pytest.ini in root dir of tests.
Content of the pytest.ini file:
```
[pytest]
mandatory fields
rp_uuid = uid reportportal
rp_endpoint = http://ip:port
rp_project = Project of ReportPortal
```
also launch tags could be added. But this parapmeter if not mandatory `rp_launch_tags = 'PyTest' 'Report_Portal'`.

### For logging of the test item flow please use the python logging util:
```python
    # import ReportPortal handler in the test module
    from pytest_reportportal.pytest_rp_plugin import RPlogHandler
    # get logger
    logger = logging.getLogger()
    # create hanler, set log level add it to the logger
    rp_handler = RPlogHandler()
    rp_handler.setLevel(logging.INFO)
    logger.addHandler(rp_handler)
    # In this case only INFO messages will be sent to the RP
    def test_one(self):
        logger.info("Case1. Step1")
        x = "this"
        logger.info("Case1. Step2")
        assert 'h' in x

### Run tests:
```bash
py.test ./tests --rp_launch AnyLaunchName

## Copyright Notice
Licensed under the [GPLv3](https://www.gnu.org/licenses/quick-guide-gplv3.html)
license (see the LICENSE file).