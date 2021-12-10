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

    assert mock_client.start_test_item.call_count == 2, \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    suite_start_kwargs = call_args[0][1]
    test_start_kwargs = call_args[1][1]

    expect(suite_start_kwargs['name'] == suite_name)
    expect(suite_start_kwargs['item_type'] == 'SUITE')
    expect(suite_start_kwargs['parent_item_id'] is None)

    expect(test_start_kwargs['name'] == test_name)
    expect(test_start_kwargs['parent_item_id'].startswith(suite_name))
    expect(test_start_kwargs['item_type'] == 'STEP')
    assert_expectations()


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

    assert mock_client.start_test_item.call_count == 3, \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    root_suite_start_kwargs = call_args[0][1]
    child_suite_start_kwargs = call_args[1][1]
    test_start_kwargs = call_args[2][1]

    expect(root_suite_start_kwargs['name'] == root_suite_name)
    expect(root_suite_start_kwargs['item_type'] == 'SUITE')
    expect(root_suite_start_kwargs['parent_item_id'] is None)

    expect(child_suite_start_kwargs['name'] == child_suite_name)
    expect(child_suite_start_kwargs['parent_item_id']
           .startswith(root_suite_name))
    expect(child_suite_start_kwargs['item_type'] == 'SUITE')

    expect(test_start_kwargs['name'] == test_name)
    expect(test_start_kwargs['parent_item_id'].startswith(child_suite_name))
    expect(test_start_kwargs['item_type'] == 'STEP')
    assert_expectations()


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

    assert mock_client.start_test_item.call_count == 4, \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    root_suite_start_kwargs = call_args[0][1]
    outer_child_suite_start_kwargs = call_args[1][1]
    inner_child_suite_start_kwargs = call_args[2][1]
    test_start_kwargs = call_args[3][1]

    expect(root_suite_start_kwargs['name'] == root_suite_name)
    expect(root_suite_start_kwargs['item_type'] == 'SUITE')
    expect(root_suite_start_kwargs['parent_item_id'] is None)

    expect(outer_child_suite_start_kwargs['name'] == outer_child_suite_name)
    expect(outer_child_suite_start_kwargs['parent_item_id']
           .startswith(root_suite_name))
    expect(outer_child_suite_start_kwargs['item_type'] == 'SUITE')

    expect(inner_child_suite_start_kwargs['name'] == inner_child_name)
    expect(inner_child_suite_start_kwargs['parent_item_id']
           .startswith(outer_child_suite_name))
    expect(inner_child_suite_start_kwargs['item_type'] == 'SUITE')

    expect(test_start_kwargs['name'] == test_name)
    expect(test_start_kwargs['parent_item_id'].startswith(inner_child_name))
    expect(test_start_kwargs['item_type'] == 'STEP')
    assert_expectations()


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

    assert mock_client.start_test_item.call_count == 4, \
        '"start_test_item" method was called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    first_suite_kwargs = call_args[0][1]
    first_test_kwargs = call_args[1][1]
    second_suite_kwargs = call_args[2][1]
    second_test_kwargs = call_args[3][1]

    expect(first_suite_kwargs['name'] == first_suite_name)
    expect(first_suite_kwargs['item_type'] == 'SUITE')
    expect(first_suite_kwargs['parent_item_id'] is None)

    expect(second_suite_kwargs['name'] == second_suite_name)
    expect(second_suite_kwargs['item_type'] == 'SUITE')
    expect(second_suite_kwargs['parent_item_id'] is None)

    expect(first_test_kwargs['name'] == test_name)
    expect(first_test_kwargs['parent_item_id'].startswith(first_suite_name))
    expect(first_test_kwargs['item_type'] == 'STEP')

    expect(second_test_kwargs['name'] == test_name)
    expect(second_test_kwargs['parent_item_id'].startswith(second_suite_name))
    expect(second_test_kwargs['item_type'] == 'STEP')

    assert_expectations()
