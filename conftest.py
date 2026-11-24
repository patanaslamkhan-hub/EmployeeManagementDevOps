import pytest
import app as app_module


@pytest.fixture(autouse=True)
def configure_rate_limiting_for_tests(request):
    limiter = app_module.limiter
    previous_enabled = limiter.enabled

    if request.node.get_closest_marker("rate_limit"):
        limiter.enabled = True
    else:
        limiter.enabled = False

    try:
        yield
    finally:
        limiter.enabled = previous_enabled
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "rate_limit: tests that verify login rate limiting"
    )
