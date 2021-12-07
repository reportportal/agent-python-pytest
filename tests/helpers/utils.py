import pytest

DEFAULT_VARIABLES = {
    'rp_launch': 'Pytest',
    'rp_endpoint': "http://localhost:8080",
    'rp_project': "default_personal",
    'rp_uuid': "test_uuid"
}


def run_pytest_tests(tests=None, variables=None):
    if variables is None:
        variables = DEFAULT_VARIABLES

    arguments = list()
    arguments.append('--reportportal')
    for k, v in variables.items():
        arguments.append('-o')
        arguments.append('{0}={1}'.format(k, str(v)))

    if tests is not None:
        for t in tests:
            arguments.append(t)

    return pytest.main(arguments)
