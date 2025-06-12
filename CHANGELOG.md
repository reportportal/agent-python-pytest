# Changelog

## [Unreleased]
### Added
- Too long BDD Step name truncation on reporting, by @HardNorth
- `use_index` parameter for `@pytest.mark.parametrize` decorator, which replaces parameter values with their indexes in the list, by @ramir-dn

## [5.5.0]
### Added
- Issue [#357](https://github.com/reportportal/agent-python-pytest/issues/357) `pytest-bdd` support, by @HardNorth
### Fixed
- Issue [#389](https://github.com/reportportal/agent-python-pytest/issues/389) `rp_tests_attributes` configuration parameter handling, by @HardNorth
- Issue [#390](https://github.com/reportportal/agent-python-pytest/issues/390) INTERNALERROR due to pytest.exit within fixture, by @HardNorth
### Removed
- `Python 3.7` support, by @HardNorth

## [5.4.7]
### Added
- Issue [#382](https://github.com/reportportal/agent-python-pytest/issues/382): Escaping of binary symbol '\0' in parameters, by @HardNorth
### Changed
- Client version updated on [5.6.0](https://github.com/reportportal/client-Python/releases/tag/5.6.0), by @HardNorth

## [5.4.6]
### Added
- Support for `Python 3.13`, by @HardNorth
- Support for `name` Pytest marker, by @HardNorth
- `rp_hierarchy_test_file` configuration parameter, which controls display of test file name in the hierarchy, by @ramir-dn, @HardNorth
### Fixed
- Agent crash if Client could not be initialized, by @HardNorth
### Changed
- Client version updated on [5.5.10](https://github.com/reportportal/client-Python/releases/tag/5.5.10), by @HardNorth

## [5.4.5]
### Fixed
- Issue [#379](https://github.com/reportportal/agent-python-pytest/issues/379): Fix TypeError when using pytest.skip() in fixtures, by @HardNorth

## [5.4.4]
### Fixed
- Issue [#375](https://github.com/reportportal/agent-python-pytest/issues/375): Fix max Item name length, by @HardNorth

## [5.4.3]
### Added
- Issue [#332](https://github.com/reportportal/agent-python-pytest/issues/332): Support for fixture reporting, by @HardNorth

## [5.4.2]
### Fixed
- Issue [#368](https://github.com/reportportal/agent-python-pytest/issues/368): Distutils in the agent, by @HardNorth
- Pytest Tavern plugin support, by @virdok
### Added
- Python 12 support, by @HardNorth

## [5.4.1]
### Fixed
- Issue [#362](https://github.com/reportportal/agent-python-pytest/issues/362): Debug mode passing, by @HardNorth

## [5.4.0]
### Added
- Pytest version >= 8 support, by @HardNorth
### Removed
- `Package` and `Dir` item types processing on test collection. This is done to preserve backward compatibility and improve name consistency, by @HardNorth
### Changed
- `rp_issue_system_url` renamed to `rp_bts_issue_url` to be consistent with other agents, by @HardNorth

## [5.3.2]
### Changed
- Set upper pytest version limit to not include `8.0.0`, by @HardNorth

## [5.3.1]
### Changed
- Client version updated on [5.5.4](https://github.com/reportportal/client-Python/releases/tag/5.5.4), by @HardNorth
- `rp_launch_id` property handling moved completely on Client side, by @HardNorth

## [5.3.0]
### Added
- `rp_client_type` configuration variable, by @HardNorth
- `rp_connect_timeout` and `rp_read_timeout` configuration variables, by @HardNorth
### Changed
- Client version updated on [5.5.2](https://github.com/reportportal/client-Python/releases/tag/5.5.2), by @HardNorth

## [5.2.2]
### Changed
- Client version updated on [5.4.1](https://github.com/reportportal/client-Python/releases/tag/5.4.1), by @HardNorth

## [5.2.1]
### Fixed
 - Log line reference for Python 3.11, by @HardNorth
### Changed
- Client version updated on [5.4.0](https://github.com/reportportal/client-Python/releases/tag/5.4.0), by @HardNorth

## [5.2.0]
### Added
- `rp_launch_uuid_print` and `rp_launch_uuid_print_output` configuration parameters, by @HardNorth
### Removed
- Python 2.7, 3.6 support, by @HardNorth

## [5.1.9]
### Added
- `rp_api_retries` configuration parameter, by @HardNorth
### Changed
- Client version updated on [5.3.5](https://github.com/reportportal/client-Python/releases/tag/5.3.5), by @HardNorth
- `rp_uuid` configuration parameter was renamed to `rp_api_key` to maintain common convention, by @HardNorth

## [5.1.8]
### Fixed
- `rp_thread_logging = False` config parameter handling, by @HardNorth
- Recursive thread init issue in case of `rp_thread_logging = True`, by @HardNorth
### Changed
- Client version updated on [5.3.2](https://github.com/reportportal/client-Python/releases/tag/5.3.2), by @HardNorth

## [5.1.7]
### Fixed
- Plugin Exception in case of Launch creation timed out, by @HardNorth
### Changed
- Client version updated on [5.3.1](https://github.com/reportportal/client-Python/releases/tag/5.3.1), by @HardNorth

## [5.1.6]
### Changed
- Client version updated on [5.3.0](https://github.com/reportportal/client-Python/releases/tag/5.3.0), by @HardNorth

## [5.1.5]
### Added
- Support of runtime issue adding, by @HardNorth

## [5.1.4]
### Added
- Feature [#325](https://github.com/reportportal/agent-python-pytest/issues/325) Support of runtime attribute adding, by @yakovbabich, @HardNorth
- `rp_launch_timeout` parameter to limit test execution in case of process hanging, by @HardNorth

## [5.1.3]
### Added
- Support for thread logs and `rp_thread_logging` flag, by @dagansandler

## [5.1.2]
### Added
- `rp_log_batch_payload_size` parameter, by @HardNorth
### Changed
- Feature [#311](https://github.com/reportportal/agent-python-pytest/issues/311):
Adding log format config option, by @dagansandler

## [5.1.1]
### Fixed
- Issue [#304](https://github.com/reportportal/agent-python-pytest/issues/304):
SSL certificate flag handling issue, by @HardNorth

## [5.1.0]
### Changed
- Agent complete rewrite, by @HardNorth
