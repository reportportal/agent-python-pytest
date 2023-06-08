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
import os
import random
import time
from multiprocessing.pool import ThreadPool

import pytest

DEFAULT_VARIABLES = {
    'rp_launch': 'Pytest',
    'rp_endpoint': 'http://localhost:8080',
    'rp_project': 'default_personal',
    'rp_api_key': 'test_api_key',
    'rp_skip_connection_test': 'True'
}

DEFAULT_PROJECT_SETTINGS = {
    'project': 2,
    'subTypes': {
        'NO_DEFECT': [
            {
                'id': 4,
                'locator': 'nd001',
                'typeRef': 'NO_DEFECT',
                'longName': 'No Defect',
                'shortName': 'ND',
                'color': "#777777"
            }
        ],
        'TO_INVESTIGATE': [
            {
                'id': 1,
                'locator': 'ti001',
                'typeRef': 'TO_INVESTIGATE',
                'longName': 'To Investigate',
                'shortName': 'TI',
                'color': '#ffb743'
            }
        ],
        'AUTOMATION_BUG': [
            {
                'id': 2,
                'locator': 'ab001',
                'typeRef': 'AUTOMATION_BUG',
                'longName': 'Automation Bug',
                'shortName': 'AB',
                'color': '#f7d63e'
            }
        ],
        'PRODUCT_BUG': [
            {
                'id': 3,
                'locator': 'pb001',
                'typeRef': 'PRODUCT_BUG',
                'longName': 'Product Bug',
                'shortName': 'PB',
                'color': '#ec3900'
            }
        ],
        'SYSTEM_ISSUE': [
            {
                'id': 5,
                'locator': 'si001',
                'typeRef': 'SYSTEM_ISSUE',
                'longName': 'System Issue',
                'shortName': 'SI',
                'color': '#0274d1'
            }
        ]
    }
}


def run_pytest_tests(tests, args=None, variables=None):
    """Run specific pytest tests.

    :param tests:     a list of tests to run
    :param args:      command line arguments which will be passed to pytest
    :param variables: parameter variables which will be passed to pytest
    :return: exit code
    """
    if args is None:
        args = []
    if variables is None:
        variables = DEFAULT_VARIABLES

    arguments = ['--reportportal'] + args
    for k, v in variables.items():
        arguments.append('-o')
        arguments.append('{0}={1}'.format(k, str(v)))

    if tests is not None:
        for t in tests:
            arguments.append(t)

    # Workaround collisions with parent test
    current_test = os.environ['PYTEST_CURRENT_TEST']
    del os.environ['PYTEST_CURRENT_TEST']
    result = pytest.main(arguments)
    os.environ['PYTEST_CURRENT_TEST'] = current_test

    return result


def item_id_gen(**kwargs):
    return "{}-{}-{}".format(kwargs['name'], str(round(time.time() * 1000)),
                             random.randint(0, 9999))


def project_settings(**kwargs):
    return DEFAULT_PROJECT_SETTINGS


def attributes_to_tuples(attributes):
    result = set()
    for attribute in attributes:
        if 'key' in attribute:
            result.add((attribute['key'], attribute['value']))
        else:
            result.add((None, attribute['value']))
    return result


# noinspection PyProtectedMember
def run_tests_with_client(client, tests, args=None, variables=None):
    def test_func():
        from reportportal_client._local import set_current
        set_current(client)
        return run_pytest_tests(tests, args, variables)

    pool = ThreadPool(processes=1)
    async_result = pool.apply_async(test_func)
    result = async_result.get()
    pool.terminate()
    return result
