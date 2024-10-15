#  Copyright 2024 EPAM Systems
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from tests.helpers import utils


# TODO: finish these tests


def test_fixture_simple():
    variables = utils.DEFAULT_VARIABLES
    result = utils.run_pytest_tests(tests=['examples/fixtures/before_test/test_fixture_setup.py'], variables=variables)
    assert int(result) == 0, 'Exit code should be 0 (no errors)'
