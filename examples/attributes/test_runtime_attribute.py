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


@pytest.mark.scope("smoke")
def test_custom_attributes_report(request):
    """
    This is a test with one custom marker as a decorator and one custom marker
    added at runtime which shall both appear on  ReportPortal on test's item
    """
    request.node.add_marker(pytest.mark.runtime())
    assert True
