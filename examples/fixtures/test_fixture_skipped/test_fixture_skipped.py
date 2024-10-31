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

import pytest


@pytest.fixture(scope="session")
def base_fixture():
    return False


@pytest.fixture()
def skip_fixture(base_fixture):
    if not base_fixture:
        pytest.skip("Skip if base condition is false")


def test_will_skip(skip_fixture):
    pass
