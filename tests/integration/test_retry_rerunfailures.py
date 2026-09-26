"""Integration tests for pytest-rerunfailures support."""

import pytest


@pytest.mark.flaky(reruns=2)
def test_eventual_pass_with_retries():
    """Test that passes after retries are properly reported."""
    if not hasattr(test_eventual_pass_with_retries, 'attempts'):
        test_eventual_pass_with_retries.attempts = 0
    test_eventual_pass_with_retries.attempts += 1

    # Passes on third attempt
    assert test_eventual_pass_with_retries.attempts >= 3


def test_without_retries():
    """Test that passes without retries."""
    assert True


@pytest.mark.flaky(reruns=1)
def test_passes_on_second_attempt():
    """Test that passes on second attempt."""
    if not hasattr(test_passes_on_second_attempt, 'count'):
        test_passes_on_second_attempt.count = 0
    test_passes_on_second_attempt.count += 1

    # Fails once, passes on second attempt
    assert test_passes_on_second_attempt.count >= 2
