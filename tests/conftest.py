import os

# ---- Environment defaults — MUST run before any application module import ----
# These are set at module level (not inside a hook/fixture) so they take effect
# before ``src.config.Settings()`` is instantiated during conftest collection.
_TEST_ENV_DEFAULTS = {
    "DATABASE_URL": "sqlite:///./test_amazon_ai.db",
    "OPENAI_API_KEY": "sk-test-placeholder",
    "FEISHU_APP_ID": "cli_test",
    "FEISHU_APP_SECRET": "test_secret",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402 — must come after env setup


def pytest_addoption(parser):
    parser.addoption(
        "--mock-external-apis",
        action="store_true",
        default=False,
        help="Mock all external API calls (Feishu, OpenAI, SellerSprite)"
    )


@pytest.fixture
def mock_external_apis(request):
    """当--mock-external-apis标志启用时，mock所有外部API"""
    if request.config.getoption("--mock-external-apis"):
        yield True
    else:
        yield False
