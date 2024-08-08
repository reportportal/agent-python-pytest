# Changelog

## [Unreleased]
## [5.4.2]
- Client version updated on [5.5.6](https://github.com/reportportal/client-Python/releases/tag/5.5.6), by @simboom

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
