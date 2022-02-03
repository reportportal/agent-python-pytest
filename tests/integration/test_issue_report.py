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
from six.moves import mock

from examples import test_issue_id
from tests import REPORT_PORTAL_SERVICE
from tests.helpers import utils
from reportportal_client.core.rp_issues import Issue

ISSUE_PLACEHOLDER = '{issue_id}'
ISSUE_URL_PATTERN = 'https://bugzilla.some.com/show_bug.cgi?id=' + \
                    ISSUE_PLACEHOLDER


@mock.patch(REPORT_PORTAL_SERVICE)
@pytest.mark.parametrize('issue_id_mark', [True, False])
def test_issue_id_attribute(mock_client_init, issue_id_mark):
    """Verify agent reports issue ids and defect type.

    :param mock_client_init: Pytest fixture
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
