import os

from setuptools import setup


def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


version = '1.0.1'
tar_url = 'https://github.com/reportportal/agent-python-pytest/tarball/1.0.1'


requirements = [
    'reportportal-client>=3.0.0',
    'pytest>=3.0.7',
    'six>=1.10.0',
]


setup(
    name='pytest-reportportal',
    version=version,
    description='Agent for Reporting results of tests to the Report Portal',
    long_description=read_file('README.rst') + '\n\n',
    author='Pavel Papou',
    author_email='SupportEPMC-TSTReportPortal@epam.com',
    url='https://github.com/reportportal/agent-python-pytest',
    download_url=tar_url,
    packages=['pytest_reportportal'],
    install_requires=requirements,
    license='GNU General Public License v3',
    keywords=['testing', 'reporting', 'reportportal', 'pytest'],
    classifiers=[
        'Framework :: Pytest',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
        ],
    entry_points={
        'pytest11': [
            'pytest_reportportal = pytest_reportportal.plugin',
        ]
    },
)
