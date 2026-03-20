#  Copyright (c) 2023 https://reportportal.io .
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

"""This module includes unit tests for the service.py module."""

from delayed_assert import assert_expectations, expect


def test_get_item_parameters(mocked_item, rp_service):
    """Test that parameters are returned in a way supported by the client."""
    mocked_item.callspec.params = {"param": "param_value"}

    expect(rp_service._get_parameters(mocked_item) == {"param": "param_value"})

    delattr(mocked_item, "callspec")
    expect(rp_service._get_parameters(mocked_item) is None)

    assert_expectations()


def test_get_method_name_regular(mocked_item, rp_service):
    """Test that regular test names are returned as-is."""
    mocked_item.name = "test_simple_function"
    mocked_item.originalname = None

    result = rp_service._get_method_name(mocked_item)

    expect(result == "test_simple_function")
    assert_expectations()


def test_get_method_name_uses_originalname(mocked_item, rp_service):
    """Test that originalname is preferred when available."""
    mocked_item.name = "test_verify_data[Daily]@sync_group"
    mocked_item.originalname = "test_verify_data"

    result = rp_service._get_method_name(mocked_item)

    expect(result == "test_verify_data")
    assert_expectations()


def test_get_method_name_strips_suffix(mocked_item, rp_service):
    """Test that trailing @suffix is stripped when originalname is None."""
    mocked_item.name = "test_export_data@data_export"
    mocked_item.originalname = None

    result = rp_service._get_method_name(mocked_item)

    expect(result == "test_export_data")
    assert_expectations()


def test_get_method_name_preserves_at_inside_params(mocked_item, rp_service):
    """Test that @ inside parameter brackets is preserved."""
    mocked_item.name = "test_email[user@example.com]"
    mocked_item.originalname = None

    result = rp_service._get_method_name(mocked_item)

    expect(result == "test_email[user@example.com]")
    assert_expectations()
