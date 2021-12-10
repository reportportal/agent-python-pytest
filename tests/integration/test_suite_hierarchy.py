"""This module includes integration tests for different suite hierarchy."""

#  Copyright (c) 2021 http://reportportal.io .
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License

import random
import time

import pytest
from delayed_assert import expect, assert_expectations
from six.moves import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


def item_id_gen(**kwargs):
    return "{}-{}-{}".format(kwargs['name'], str(round(time.time() * 1000)),
                             random.randint(0, 9999))


def verify_start_item_parameters(mock_client, expected_items):
    assert mock_client.start_test_item.call_count == len(expected_items), \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    for i, call in enumerate(call_args):
        start_kwargs = call[1]
        expect(start_kwargs['name'] == expected_items[i]['name'])
        expect(start_kwargs['item_type'] == expected_items[i]['item_type'])
        verification = expected_items[i]['parent_item_id']
        expect(verification(start_kwargs['parent_item_id']))
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize('suite_name', ('examples/test_simple.py',
                                        'examples/inner/test_inner_simple.py'))
def test_simple_test_in_folder(mock_client_init, suite_name):
    """Verify correct suite name and type for different test folders.

    :param mock_client_init: Pytest fixture
    :param suite_name: a path to a test to run
    """
    test_name = 'test_simple'

    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = item_id_gen

    result = utils.run_pytest_tests(tests=[suite_name])
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expected_items = [
        {'name': suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': test_name, 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(suite_name)}
    ]

    verify_start_item_parameters(mock_client, expected_items)


@mock.patch(REPORT_PORTAL_SERVICE)
def test_simple_test_in_class(mock_client_init):
    """Verify correct suite name and type for a test in a class.

    :param mock_client_init: Pytest fixture
    """
    root_suite_name = 'examples/test_in_class.py'
    child_suite_name = 'Tests'
    test_name = 'test_in_class'

    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = item_id_gen

    result = utils.run_pytest_tests(tests=[root_suite_name])
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expected_items = [
        {'name': root_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': child_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(root_suite_name)},
        {'name': test_name, 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(child_suite_name)}
    ]

    verify_start_item_parameters(mock_client, expected_items)


@mock.patch(REPORT_PORTAL_SERVICE)
def test_simple_test_in_class_in_class(mock_client_init):
    """Verify correct suite name and type for a test in a class in a class.

    :param mock_client_init: Pytest fixture
    """
    root_suite_name = 'examples/test_in_class_in_class.py'
    outer_child_suite_name = 'Tests'
    inner_child_name = 'Test'
    test_name = 'test_in_class_in_class'

    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = item_id_gen

    result = utils.run_pytest_tests(tests=[root_suite_name])
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expected_items = [
        {'name': root_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': outer_child_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(root_suite_name)},
        {'name': inner_child_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(outer_child_suite_name)},
        {'name': test_name, 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(inner_child_name)}
    ]

    verify_start_item_parameters(mock_client, expected_items)


@mock.patch(REPORT_PORTAL_SERVICE)
def test_simple_tests_in_different_inner_folders(mock_client_init):
    """Verify correct suite hierarchy for two tests in different folders.

    :param mock_client_init: Pytest fixture
    """
    tests_to_run = ['examples/another_inner/test_another_inner_simple.py',
                    'examples/inner/test_inner_simple.py']
    first_suite_name = 'examples/another_inner/test_another_inner_simple.py'
    second_suite_name = 'examples/inner/test_inner_simple.py'
    test_name = 'test_simple'

    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = item_id_gen

    result = utils.run_pytest_tests(tests=tests_to_run)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    expected_items = [
        {'name': first_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': test_name, 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(first_suite_name)},
        {'name': second_suite_name, 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': test_name, 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(second_suite_name)}
    ]

    verify_start_item_parameters(mock_client, expected_items)
