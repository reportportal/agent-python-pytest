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

from pytest_bdd import given, scenarios, then

scenarios("../features/background_two_steps.feature")


@given("I have first empty step")
def first_empty_step():
    """First empty step implementation."""
    pass


@given("I have second empty step")
def second_empty_step():
    """Second empty step implementation."""
    pass


@then("I have main step")
def main_step():
    """Main step implementation."""
    pass
