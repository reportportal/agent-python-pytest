"""This module contains utility code for unit tests.

Copyright (c) 2021 https://reportportal.io .
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License
"""
import pytest

DEFAULT_VARIABLES = {
    'rp_launch': 'Pytest',
    'rp_endpoint': "http://localhost:8080",
    'rp_project': "default_personal",
    'rp_uuid': "test_uuid",
    'rp_hierarchy_dir_path_separator': '/'
}


def run_pytest_tests(tests=None, variables=None):
    """Run specific pytest tests.

    :param tests:     a list of tests to run
    :param variables: parameter  variables which will be passed to pytest
    :return: exit code
    """
    if variables is None:
        variables = DEFAULT_VARIABLES

    arguments = ['--reportportal']
    for k, v in variables.items():
        arguments.append('-o')
        arguments.append('{0}={1}'.format(k, str(v)))

    if tests is not None:
        for t in tests:
            arguments.append(t)

    return pytest.main(arguments)
