"""Config for setup package pytest agent."""

import os

from setuptools import setup


__version__ = '5.1.8'


def read_file(fname):
    """Read the given file.

    :param fname: Filename to be read
    :return:      File content
    """
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='pytest-reportportal',
    version=__version__,
    description='Agent for Reporting results of tests to the Report Portal',
    long_description=read_file('README.rst'),
    long_description_content_type='text/x-rst',
    author='Report Portal Team',
    author_email='support@reportportal.io',
    url='https://github.com/reportportal/agent-python-pytest',
    packages=['pytest_reportportal'],
    package_data={'pytest_reportportal': ['*.pyi']},
    install_requires=read_file('requirements.txt').splitlines(),
    license='Apache 2.0',
    keywords=['testing', 'reporting', 'reportportal', 'pytest', 'agent'],
    classifiers=[
        'Framework :: Pytest',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
        ],
    entry_points={
        'pytest11': [
            'pytest_reportportal = pytest_reportportal.plugin',
        ]
    }
)
