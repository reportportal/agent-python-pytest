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

from pytest_reportportal.config import AgentConfig


@pytest.mark.parametrize(
    ["verify_ssl", "expected_result"],
    [
        ("True", True),
        ("False", False),
        ("true", True),
        ("false", False),
        (True, True),
        (False, False),
        ("path/to/certificate", "path/to/certificate"),
        (None, True),
    ],
)
def test_verify_ssl_true(mocked_config, verify_ssl, expected_result):
    mocked_config.getini.side_effect = lambda x: verify_ssl if x == "rp_verify_ssl" else None
    config = AgentConfig(mocked_config)

    assert config.rp_verify_ssl == expected_result


@pytest.mark.parametrize(
    ["env_var", "env_value", "config_attr", "expected"],
    [
        ("RP_ENDPOINT", "http://env.example.com", "rp_endpoint", "http://env.example.com"),
        ("RP_PROJECT", "env_project", "rp_project", "env_project"),
        ("RP_LAUNCH", "env_launch", "rp_launch", "env_launch"),
        ("RP_API_KEY", "env_api_key", "rp_api_key", "env_api_key"),
        ("RP_LAUNCH_UUID", "env_launch_id", "rp_launch_uuid", "env_launch_id"),
        ("RP_MODE", "DEBUG", "rp_mode", "DEBUG"),
        ("RP_PARENT_ITEM_ID", "env_parent_id", "rp_parent_item_id", "env_parent_id"),
        ("RP_RERUN_OF", "env_rerun_of", "rp_rerun_of", "env_rerun_of"),
    ],
)
def test_env_var_overrides_config(monkeypatch, mocked_config, env_var, env_value, config_attr, expected):
    monkeypatch.setenv(env_var, env_value)
    config = AgentConfig(mocked_config)
    assert getattr(config, config_attr) == expected


def test_env_var_overrides_verify_ssl(monkeypatch, mocked_config):
    monkeypatch.setenv("RP_VERIFY_SSL", "False")
    config = AgentConfig(mocked_config)
    assert config.rp_verify_ssl is False


def test_env_var_overrides_enabled(monkeypatch, mocked_config):
    mocked_config.option.rp_enabled = False
    monkeypatch.setenv("RP_ENABLED", "True")
    config = AgentConfig(mocked_config)
    assert config.rp_enabled is True


def test_env_var_overrides_log_level(monkeypatch, mocked_config):
    import logging

    monkeypatch.setenv("RP_LOG_LEVEL", "ERROR")
    config = AgentConfig(mocked_config)
    assert config.rp_log_level == logging.ERROR


def test_env_var_not_set_falls_back_to_config(mocked_config):
    config = AgentConfig(mocked_config)
    assert config.rp_endpoint == "http://docker.local:8080/"
