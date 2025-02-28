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

import logging

from pytest_bdd import given, parsers, scenarios, then, when

# Import the scenario from the feature file
scenarios("../features/scenario_outline_background.feature")


LOGGER = logging.getLogger(__name__)


@given("I have empty step in background")
def empty_step():
    """Empty step implementation."""
    pass


@given("It is test with parameters")
def step_with_parameters():
    LOGGER.info("It is test with parameters")


@when(parsers.parse('I have parameter "{parameter}"'))
def have_parameter_str(parameter: str):
    LOGGER.info("String parameter %s", parameter)


@then(parsers.parse("I emit number {parameters:d} on level info"))
def emit_number_info(parameters):
    LOGGER.info("Test with parameters: %d", parameters)
