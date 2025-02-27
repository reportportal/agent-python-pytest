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
from typing import Dict

from pytest_bdd import given, parsers, scenarios

# Import the scenario from the feature file
scenarios("../features/data_table_parameter.feature")


LOGGER = logging.getLogger(__name__)


@given("a step with a data table:")
def step_with_data_table(datatable: Dict[str, str]) -> None:
    """Step that receives a data table and logs its content.

    :param datatable: Data table from the feature file
    """
    LOGGER.info("Data table content: %s", datatable)
