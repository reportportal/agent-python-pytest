"""This module includes integration test for issue type reporting."""

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
import pytest
from delayed_assert import expect, assert_expectations
from reportportal_client.core.rp_issues import Issue
from unittest import mock

from examples import test_issue_id
from pytest_reportportal.service import NOT_ISSUE
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils

ISSUE_PLACEHOLDER = '{issue_id}'
ISSUE_URL_PATTERN = 'https://bugzilla.some.com/show_bug.cgi?id=' + \
                    ISSUE_PLACEHOLDER
BTS_PROJECT = 'RP-TEST'
BTS_URL = 'https://bugzilla.some.com'


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize('issue_id_mark', [True, False])
def test_issue_id_attribute(mock_client_init, issue_id_mark):
    """Verify agent reports issue attribute if configured.

    :param mock_client_init: Pytest fixture
    :param issue_id_mark:    Attribute report configuration
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen
    mock_client.get_project_settings.side_effect = utils.project_settings

    variables = dict()
    variables['rp_issue_id_marks'] = issue_id_mark
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_issue_id.py'],
                                    variables=variables)
    assert int(result) == 1, 'Exit code should be 1 (test failed)'

    call_args = mock_client.start_test_item.call_args_list
    finish_test_step = call_args[-1][1]
    attributes = finish_test_step['attributes']

    if issue_id_mark:
        assert len(attributes) == 1
        issue_attribute = attributes[0]
        expect(issue_attribute['key'] == 'issue')
        expect(issue_attribute['value'] == test_issue_id.ID)
        assert_expectations()
    else:
        assert len(attributes) == 0


@mock.patch(REPORT_PORTAL_SERVICE)
def test_issue_report(mock_client_init):
    """Verify agent reports issue ids and defect type.

    :param mock_client_init: Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen
    mock_client.get_project_settings.side_effect = utils.project_settings

    variables = dict()
    variables['rp_issue_system_url'] = ISSUE_URL_PATTERN
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_issue_id.py'],
                                    variables=variables)
    assert int(result) == 1, 'Exit code should be 1 (test failed)'

    call_args = mock_client.finish_test_item.call_args_list
    finish_test_step = call_args[0][1]
    issue = finish_test_step['issue']

    assert isinstance(issue, Issue)
    expect(issue.issue_type == 'pb001')
    expect(issue.comment is not None)
    assert_expectations()
    comments = issue.comment.split('\n')
    assert len(comments) == 1
    comment = comments[0]
    assert comment == "* {}: [{}]({})" \
        .format(test_issue_id.REASON, test_issue_id.ID,
                ISSUE_URL_PATTERN.replace(ISSUE_PLACEHOLDER, test_issue_id.ID))


@mock.patch(REPORT_PORTAL_SERVICE)
def test_passed_no_issue_report(mock_client_init):
    """Verify agent do not report issue if test passed.

    :param mock_client_init: Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen
    mock_client.get_project_settings.side_effect = utils.project_settings

    variables = dict()
    variables['rp_issue_system_url'] = ISSUE_URL_PATTERN
    variables.update(utils.DEFAULT_VARIABLES.items())
    result = utils.run_pytest_tests(tests=['examples/test_issue_id_pass.py'],
                                    variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no failures)'

    call_args = mock_client.finish_test_item.call_args_list
    finish_test_step = call_args[0][1]
    assert 'issue' not in finish_test_step or finish_test_step['issue'] is None


@pytest.mark.parametrize(('flag_value', 'expected_issue'), [(True, None),
                                                            (False, NOT_ISSUE),
                                                            (None, None)])
@mock.patch(REPORT_PORTAL_SERVICE)
def test_skipped_not_issue(mock_client_init, flag_value, expected_issue):
    """Verify 'rp_is_skipped_an_issue' option handling.

    :param mock_client_init: mocked Report Portal client Pytest fixture
    :param flag_value:       option value to set during the test
    :param expected_issue:   result issue value to verify
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen

    variables = dict()
    if flag_value is not None:
        variables['rp_is_skipped_an_issue'] = flag_value
    variables.update(utils.DEFAULT_VARIABLES.items())

    result = utils.run_pytest_tests(
        tests=['examples/skip/test_simple_skip.py'],
        variables=variables
    )

    assert int(result) == 0, 'Exit code should be 0 (no failures)'
    call_args = mock_client.finish_test_item.call_args_list
    finish_test_step = call_args[0][1]
    actual_issue = finish_test_step.get('issue', None)
    assert actual_issue == expected_issue


@mock.patch(REPORT_PORTAL_SERVICE)
def test_skipped_custom_issue(mock_client_init):
    """Verify skipped test with issue decorator handling.

    :param mock_client_init: mocked Report Portal client Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen
    mock_client.get_project_settings.side_effect = utils.project_settings

    variables = dict()
    variables['rp_is_skipped_an_issue'] = True
    variables['rp_issue_system_url'] = ISSUE_URL_PATTERN
    variables.update(utils.DEFAULT_VARIABLES.items())

    result = utils.run_pytest_tests(tests=['examples/skip/test_skip_issue.py'],
                                    variables=variables)

    assert int(result) == 0, 'Exit code should be 0 (no failures)'
    call_args = mock_client.finish_test_item.call_args_list
    finish_test_step = call_args[0][1]
    actual_issue = finish_test_step.get('issue', None)
    assert isinstance(actual_issue, Issue)
    expect(actual_issue.issue_type == 'pb001')
    expect(actual_issue.comment is not None)
    assert_expectations()


@mock.patch(REPORT_PORTAL_SERVICE)
def test_external_issue(mock_client_init):
    """Verify skipped test with issue decorator handling.

    :param mock_client_init: mocked Report Portal client Pytest fixture
    """
    mock_client = mock_client_init.return_value
    mock_client.start_test_item.side_effect = utils.item_id_gen
    mock_client.get_project_settings.side_effect = utils.project_settings

    variables = dict()
    variables['rp_bts_project'] = BTS_PROJECT
    variables['rp_bts_url'] = BTS_URL
    variables['rp_issue_system_url'] = ISSUE_URL_PATTERN
    variables.update(utils.DEFAULT_VARIABLES.items())

    result = utils.run_pytest_tests(tests=['examples/test_issue_id.py'],
                                    variables=variables)

    assert int(result) == 1, 'Exit code should be 1 (test failed)'
    call_args = mock_client.finish_test_item.call_args_list
    finish_test_step = call_args[0][1]
    actual_issue = finish_test_step.get('issue', None)
    assert isinstance(actual_issue, Issue)
    expect(actual_issue.issue_type == 'pb001')
    expect(actual_issue.comment is not None)
    external_issues = actual_issue._external_issues
    expect(len(external_issues) == 1)
    assert_expectations()
    external_issue = external_issues[0]
    expect(external_issue['btsUrl'] == BTS_URL)
    expect(external_issue['btsProject'] == BTS_PROJECT)
    expect(external_issue['ticketId'] == test_issue_id.ID)
    expect(external_issue['url'] ==
           ISSUE_URL_PATTERN.replace(ISSUE_PLACEHOLDER, test_issue_id.ID))
    assert_expectations()
