from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

version = '0.2.1'
requirements = [
    "reportportal_client"
]

setup(
    name='pytest-reportportal',
    version=version,
    description="Framework integration with PyTest",
    long_description=readme + '\n\n',
    author="Pavel Papou",
    author_email='pavel_papou@epam.com',
    url='https://github.com/reportportal/agent-python-pytest',
    packages=['pytest_reportportal'],
    install_requires=requirements,
    license="GNU General Public License v3",
    keywords=['testing', 'reporting', 'reportportal', 'pytest'],
    classifiers=[
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'],
    entry_points={
        'pytest11': [
            'pytest_reportportal = pytest_reportportal.pytest_rp_plugin',
        ]
    },
)
