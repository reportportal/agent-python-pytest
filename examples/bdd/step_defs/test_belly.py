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

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/belly.feature")


@given(parsers.parse("I have {start:d} cukes in my belly"), target_fixture="cucumbers")
def given_cucumbers(start):
    return {"start": start, "wait": 0}


@when(parsers.parse("I wait {hours:d} hour"))
def then_wait(cucumbers, hours):
    cucumbers["wait"] += hours


@then("my belly should growl")
def assert_growl(cucumbers):
    assert cucumbers["start"] == cucumbers["wait"] * 42
