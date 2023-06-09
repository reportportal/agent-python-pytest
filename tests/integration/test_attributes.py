"""This module includes integration tests for different attribute reporting."""
#  Copyright (c) 2022 https://reportportal.io .
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

from unittest import mock

from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils


@mock.patch(REPORT_PORTAL_SERVICE)
def test_custom_attribute_report(mock_client_init):
    """Verify custom attribute is reported.

    :param mock_client_init: Pytest fixture
    """
    variables = {
        'markers': 'scope: to which test scope a test relates'
    }
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=['examples/attributes/test_one_attribute.py'],
        variables=variables
    )
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    assert step_call_args['attributes'] == [{'key': 'scope', 'value': 'smoke'}]


@mock.patch(REPORT_PORTAL_SERVICE)
def test_custom_attribute_not_reported_if_skip_configured(mock_client_init):
    """Verify custom attribute is not reported if it's configured as skipped.

    :param mock_client_init: Pytest fixture
    """
    variables = {
        'markers': 'scope: to which test scope a test relates',
        'rp_ignore_attributes': 'scope'
    }
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=['examples/attributes/test_one_attribute.py'],
        variables=variables
    )
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    assert step_call_args['attributes'] == []


@mock.patch(REPORT_PORTAL_SERVICE)
def test_two_attributes_different_values_report(mock_client_init):
    """Verify two attributes with different values is reported.

    :param mock_client_init: Pytest fixture
    """
    variables = {
        'markers': 'scope: to which test scope a test relates'
    }
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=['examples/attributes/test_two_attributes_with_same_key.py'],
        variables=variables
    )
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    actual_attributes = step_call_args['attributes']

    assert utils.attributes_to_tuples(actual_attributes) == {
        ('scope', 'smoke'),
        ('scope', 'regression')
    }


@mock.patch(REPORT_PORTAL_SERVICE)
def test_skip_attribute(mock_client_init):
    """Skip attribute is reported as tag.

    :param mock_client_init: Pytest fixture
    """
    result = utils.run_pytest_tests(
        tests=['examples/skip/test_simple_skip.py'])
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'

    call_args = mock_client.start_test_item.call_args_list
    step_call_args = call_args[-1][1]
    actual_attributes = step_call_args['attributes']

    assert utils.attributes_to_tuples(actual_attributes) == {
        (None, 'skip')
    }


@mock.patch(REPORT_PORTAL_SERVICE)
def test_custom_runtime_attribute_report(mock_client_init):
    """Verify custom attribute is reported.

    :param mock_client_init: Pytest fixture
    """
    variables = {
        'markers': 'scope: to which test scope a test relates\n'
                   'runtime: runtime attribute mark'
    }
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(
        tests=['examples/attributes/test_runtime_attribute.py'],
        variables=variables
    )
    assert int(result) == 0, 'Exit code should be 0 (no errors)'

    mock_client = mock_client_init.return_value
    assert mock_client.start_test_item.call_count > 0, \
        '"start_test_item" called incorrect number of times'
    assert mock_client.finish_test_item.call_count > 0, \
        '"finish_test_item" called incorrect number of times'

    start_call_args = mock_client.start_test_item.call_args_list
    start_step_call_args = start_call_args[-1][1]
    assert start_step_call_args['attributes'] == [
        {'key': 'scope', 'value': 'smoke'}
    ]

    finish_call_args = mock_client.finish_test_item.call_args_list
    finish_step_call_args = finish_call_args[-1][1]
    actual_attributes = finish_step_call_args['attributes']
    attribute_tuple_list = [(kv.get('key'), kv['value'])
                            for kv in actual_attributes]

    assert set(attribute_tuple_list) == {('scope', 'smoke'), (None, 'runtime')}
