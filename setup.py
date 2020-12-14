"""Config for setup package pytest agent."""

import os

from setuptools import setup


__version__ = '5.0.7'


def read_file(fname):
    """
    Read file.

    :param fname: string of filename
    :return: File descriptor
    """
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='pytest-reportportal',
    version=__version__,
    description='Agent for Reporting results of tests to the Report Portal',
    long_description=read_file('README.rst'),
    long_description_content_type='text/markdown',
    author_email='SupportEPMC-TSTReportPortal@epam.com',
    url='https://github.com/reportportal/agent-python-pytest',
    packages=['pytest_reportportal'],
    install_requires=read_file('requirements.txt').splitlines(),
    license='Apache 2.0',
    keywords=['testing', 'reporting', 'reportportal', 'pytest'],
    classifiers=[
        'Framework :: Pytest',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
        ],
    entry_points={
        'pytest11': [
            'pytest_reportportal = pytest_reportportal.plugin',
        ]
    },
    setup_requires=['pytest-runner'],
    tests_require=[
        'pytest',
        'delayed-assert'
    ]
)
