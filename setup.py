import os
from setuptools import setup


def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


version = "0.2.3"
requirements = [
    "reportportal-client>=2.5.4",
    "pytest>=3.0.7",
    "six>=1.10.0"]

setup(
    name="pytest-reportportal",
    version=version,
    description="Agent for Reproting results of tests to the Report Portal server",
    long_description=read_file("README.md") + "\n\n",
    author="Pavel Papou",
    author_email="SupportEPMC-TSTReportPortal@epam.com",
    url="https://github.com/reportportal/agent-python-pytest",
    packages=['pytest_reportportal'],
    install_requires=requirements,
    license="GNU General Public License v3",
    keywords=["testing", "reporting", "reportportal", "pytest"],
    classifiers=[
        "Framework :: Pytest",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
        ],
    entry_points={
        "pytest11": [
            "pytest_reportportal = pytest_reportportal.plugin",
        ]
    },
)
