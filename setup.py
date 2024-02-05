#  Copyright (c) 2023 EPAM Systems
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

"""Config for setup package pytest agent."""

import os

from setuptools import setup


__version__ = '5.3.2'


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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11'
        ],
    entry_points={
        'pytest11': [
            'pytest_reportportal = pytest_reportportal.plugin',
        ]
    }
)
