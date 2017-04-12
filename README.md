# agent-python-pytest
Framework integration with PyTest

Description:
Plugin for reporting items results of Pytest to the 'Reportal Portal'.

Install Plugin
pip install pytest-reportportal

Usage:

Prepare the config file pytest.ini in root dir of tests.
Content of the pytest.ini file:
  [pytest]
  rp_uuid = uid reportportal
  rp_endpoint = http://ip:port
  rp_project = Project of ReportPortal

Run tests:
py.test ./tests --rp_launch AnyLaunchName

Features:
  - add logging
  - add Tags parameter to config file