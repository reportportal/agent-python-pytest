"""A simple example test with Test Case ID decorator and parameters."""
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

TEST_CASE_ID = "ISSUE-321"


@pytest.mark.parametrize(('param1', 'param2'), [('value1', 'value2')])
@pytest.mark.tc_id(TEST_CASE_ID, parameterized=False)
def test_case_id_decorator(param1, param2):
    assert True
