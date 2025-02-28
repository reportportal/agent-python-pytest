#  Copyright 2025 EPAM Systems
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

"""Rule keyword test module."""
from pytest_bdd import given, scenarios, then

scenarios("../features/rule_keyword.feature")


@given("I have empty step")
def empty_step():
    """Empty step implementation."""
    pass


@then("I have another empty step")
def another_empty_step():
    """Another empty step implementation."""
    pass


@then("I have one more empty step")
def one_more_empty_step():
    """One more empty step implementation."""
    pass


@then("I have one more else empty step")
def one_more_else_empty_step():
    """One more else empty step implementation."""
    pass
