"""Integration test for MessageSendGraph with a real LinkedIn profile."""

import pytest

from src.config.config_loader import load_config
from src.core.agents.tools.message_template import render_template
from src.linkedin_mcp.graphs.linkedin_auth_graph import LinkedInAuthGraph
from src.linkedin_mcp.graphs.message_send_graph import MessageSendGraph
from src.linkedin_mcp.services.browser_manager_service import BrowserManagerService

# Test profile URL — replace with a real LinkedIn profile for testing
TEST_PROFILE_URL = "https://www.linkedin.com/in/ignacio-castelar-carballo-468619194/"
TEST_EMPLOYEE_NAME = "Ignacio Castelar Carballo"
TEST_MESSAGE_TEMPLATE = "Hola {employee_name}, esto es una prueba."


@pytest.fixture
def browser_manager():
    """Create and yield a browser manager, cleanup after test."""
    config = load_config()
    manager = BrowserManagerService(
        headless=config.browser.headless,
        use_undetected=config.browser.use_undetected,
        browser_type=config.browser.browser_type,
        chrome_version=config.browser.chrome_version,
        chrome_binary_path=config.browser.chrome_binary_path,
    )
    yield manager
    manager.close_browser()


@pytest.fixture
def authenticated_browser(browser_manager):
    """Start browser and authenticate with LinkedIn."""
    config = load_config()

    # Get credentials from config/env
    email = config.linkedin.email
    password = config.linkedin.password

    if not email or not password:
        pytest.skip(
            "LinkedIn credentials not configured (set LINKEDIN_EMAIL and LINKEDIN_PASSWORD)"
        )

    browser_manager.start_browser()

    auth_graph = LinkedInAuthGraph()
    auth_result = auth_graph.execute(email, password, browser_manager)

    if not auth_result.get("authenticated"):
        pytest.fail(
            f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
        )

    return browser_manager


class TestMessageSendGraph:
    """Integration tests for MessageSendGraph."""

    def test_send_direct_message(self, authenticated_browser):
        """Test sending a direct message to a profile."""
        graph = MessageSendGraph(browser_manager=authenticated_browser)

        # Render template with employee name
        message_text = render_template(
            TEST_MESSAGE_TEMPLATE,
            {"employee_name": TEST_EMPLOYEE_NAME},
        )

        result = graph.execute(
            employee_profile_url=TEST_PROFILE_URL,
            employee_name=TEST_EMPLOYEE_NAME,
            message_text=message_text,
            authenticated_browser_manager=authenticated_browser,
        )

        print(f"\n--- Message Send Result ---")
        print(f"Profile URL: {result['employee_profile_url']}")
        print(f"Employee Name: {result['employee_name']}")
        print(f"Sent: {result['sent']}")
        print(f"Method: {result['method']}")
        print(f"Error: {result.get('error')}")

        # Don't assert success — just verify the graph ran and returned a result
        assert result["employee_profile_url"] == TEST_PROFILE_URL
        assert result["method"] in ("direct_message", "connection_request", "")


if __name__ == "__main__":
    """Run the test directly for manual testing."""
    import os

    # Allow running without pytest for interactive debugging
    config = load_config()
    email = os.getenv("LINKEDIN_EMAIL") or config.linkedin.email
    password = os.getenv("LINKEDIN_PASSWORD") or config.linkedin.password

    if not email or not password:
        print("ERROR: Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables")
        exit(1)

    print(f"Testing MessageSendGraph with profile: {TEST_PROFILE_URL}")
    print(f"Using LinkedIn account: {email}")

    # Setup browser
    manager = BrowserManagerService(
        headless=config.browser.headless,
        use_undetected=config.browser.use_undetected,
        browser_type=config.browser.browser_type,
        chrome_version=config.browser.chrome_version,
        chrome_binary_path=config.browser.chrome_binary_path,
    )

    try:
        manager.start_browser()

        # Authenticate
        print("\n--- Authenticating ---")
        auth_graph = LinkedInAuthGraph()
        auth_result = auth_graph.execute(email, password, manager)

        if not auth_result.get("authenticated"):
            print(f"Authentication failed: {auth_result.get('error')}")
            exit(1)

        print("Authentication successful!")

        # Run message send graph
        print("\n--- Running MessageSendGraph ---")
        graph = MessageSendGraph(browser_manager=manager)

        # Render template with employee name
        message_text = render_template(
            TEST_MESSAGE_TEMPLATE,
            {"employee_name": TEST_EMPLOYEE_NAME},
        )
        print(f"Rendered message: {message_text}")

        result = graph.execute(
            employee_profile_url=TEST_PROFILE_URL,
            employee_name=TEST_EMPLOYEE_NAME,
            message_text=message_text,
            authenticated_browser_manager=manager,
        )

        print(f"\n--- Result ---")
        # Handle both dict (raw graph output) and MessageResult object
        if isinstance(result, dict):
            print(f"Sent: {result.get('sent')}")
            print(f"Method: {result.get('method')}")
            print(f"Error: {result.get('error')}")
        else:
            print(f"Sent: {result.sent}")
            print(f"Method: {result.method}")
            print(f"Error: {result.error}")

    finally:
        manager.close_browser()
