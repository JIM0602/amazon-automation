import pytest


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
