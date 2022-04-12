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
    [['examples/params/test_in_class_parameterized.py']] * 5 + \
    [['examples/hierarchy/inner/test_inner_simple.py']] * 7 + \
    [['examples/hierarchy/test_in_class_in_class.py']]

# noinspection PyTypeChecker
HIERARCHY_TEST_VARIABLES = \
    [dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_code': True},
          **utils.DEFAULT_VARIABLES)] * 6 + \
    [
        dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_code': True,
              'rp_hierarchy_dirs_level': 1}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_code': True,
              'rp_hierarchy_dirs_level': 2}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_code': True,
              'rp_hierarchy_dirs_level': 999}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs': True, 'rp_hierarchy_code': True,
              'rp_hierarchy_dirs_level': -1}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dir_path_separator': '/',
              'rp_hierarchy_code': True}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dir_path_separator': '\\',
              'rp_hierarchy_code': True}, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs_level': 1, 'rp_hierarchy_code': True,
              }, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs_level': 2, 'rp_hierarchy_code': True,
              }, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs_level': 999, 'rp_hierarchy_code': True,
              }, **utils.DEFAULT_VARIABLES),
        dict({'rp_hierarchy_dirs_level': -1, 'rp_hierarchy_code': True,
              }, **utils.DEFAULT_VARIABLES),
        dict(**utils.DEFAULT_VARIABLES),
        dict(**utils.DEFAULT_VARIABLES)
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
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'hierarchy', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_in_class.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('hierarchy')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('test_in_class.py')},
        {'name': 'test_in_class', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'hierarchy', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_in_class_in_class.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('hierarchy')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x:
         x.startswith('test_in_class_in_class.py')},
        {'name': 'Test', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('Tests')},
        {'name': 'test_in_class_in_class', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Test')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'hierarchy', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'another_inner', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('hierarchy')},
        {'name': 'test_another_inner_simple.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('another_inner')},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith(
             'test_another_inner_simple.py')},
        {'name': 'inner', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('hierarchy')},
        {'name': 'test_inner_simple.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('inner')},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('test_inner_simple.py')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'params', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('params')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'params', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('params')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
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
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'examples', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x is None},
        {'name': 'params', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('examples')},
        {'name': 'test_in_class_parameterized.py', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith('params')},
        {'name': 'Tests', 'item_type': 'SUITE',
         'parent_item_id': lambda x: x.startswith(
             'test_in_class_parameterized.py')},
        {'name': 'test_in_class_parameterized[param]', 'item_type': 'STEP',
         'parent_item_id': lambda x: x.startswith('Tests')}
    ],
    [
        {'name': 'examples/hierarchy/inner/test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('examples/hierarchy/inner/test_inner_simple.py')}
    ],
    [
        {'name': 'examples\\hierarchy\\inner\\test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('examples\\hierarchy\\inner\\test_inner_simple.py')}
    ],
    [
        {'name': 'hierarchy/inner/test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('hierarchy/inner/test_inner_simple.py')}
    ],
    [
        {'name': 'inner/test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('inner/test_inner_simple.py')}
    ],
    [
        {'name': 'test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('test_inner_simple.py')}
    ],
    [
        {'name': 'examples/hierarchy/inner/test_inner_simple.py',
         'item_type': 'SUITE', 'parent_item_id': lambda x: x is None},
        {'name': 'test_simple', 'item_type': 'STEP',
         'parent_item_id':
             lambda x:
             x.startswith('examples/hierarchy/inner/test_inner_simple.py')}
    ],
    [
        {'name': 'examples/hierarchy/inner/test_inner_simple.py::test_simple',
         'item_type': 'STEP', 'parent_item_id': lambda x: x is None}
    ],
    [
        {'name': 'examples/hierarchy/test_in_class_in_class.py::Tests::Test'
                 '::test_in_class_in_class',
         'item_type': 'STEP', 'parent_item_id': lambda x: x is None}
    ]
]

HIERARCHY_TEST_PARAMETERS = [
    (test, HIERARCHY_TEST_VARIABLES[idx], HIERARCHY_TEST_EXPECTED_ITEMS[idx])
    for
    idx, test in
    enumerate(HIERARCHY_TESTS)
]
