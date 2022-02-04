"""This package contains integration tests for the project.

Copyright (c) 2021 https://reportportal.io .
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License
"""
from tests.helpers import utils

HIERARCHY_TESTS = \
    [
        ['examples/test_simple.py'],
        ['examples/hierarchy/inner/test_inner_simple.py'],
        ['examples/hierarchy/test_in_class.py'],
        ['examples/hierarchy/test_in_class_in_class.py'],
        ['examples/hierarchy/another_inner/test_another_inner_simple.py',
         'examples/hierarchy/inner/test_inner_simple.py']
    ] + \
    [['examples/test_in_class_parameterized.py'] for _ in range(7)]

HIERARCHY_TEST_VARIABLES = \
    [utils.DEFAULT_VARIABLES] * 5 + \
    [
        dict({'rp_hierarchy_dirs': True}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_module': False}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_module': False},
             **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_parametrize': True, 'rp_hierarchy_module': False},
             **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_module': False,
              'rp_display_suite_test_file': False},
             **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs_level': 1}, **utils.DEFAULT_VARIABLES),
        dict(utils.DEFAULT_VARIABLES,
             **{'rp_hierarchy_dir_path_separator': '\\'})
    ]

HIERARCHY_TEST_EXPECTED_ITEMS = [
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_simple.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('test_simple.py')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'hierarchy', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'inner', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('hierarchy')},
        {'name': 'test_inner_simple.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('inner')},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('test_inner_simple.py')}
    ],
    [
        {'name': HIERARCHY_TESTS[2][0], 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(HIERARCHY_TESTS[2][0])},
        {'name': 'test_in_class', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': HIERARCHY_TESTS[3][0], 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(HIERARCHY_TESTS[3][0])},
        {'name': 'Test', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('Tests')},
        {'name': 'test_in_class_in_class', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Test')}
    ],
    [
        {'name': HIERARCHY_TESTS[4][0], 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(HIERARCHY_TESTS[4][0])},
        {'name': HIERARCHY_TESTS[4][1], 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(HIERARCHY_TESTS[4][1])}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'examples/test_in_class_parameterized.py::Tests',
         'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(
             'examples/test_in_class_parameterized.py::Tests')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized.py::Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py::Tests')}
    ],
    [
        {'name': 'examples/test_in_class_parameterized.py::Tests',
         'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'examples/test_in_class_parameterized.py::Tests')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized')}
    ],
    [
        {'name': 'Tests',
         'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'examples\\test_in_class_parameterized.py',
         'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'examples\\test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ]
]

HIERARCHY_TEST_PARAMETERS = [
    (test, HIERARCHY_TEST_VARIABLES[idx], HIERARCHY_TEST_EXPECTED_ITEMS[idx])
    for
    idx, test in
    enumerate(HIERARCHY_TESTS)
]
