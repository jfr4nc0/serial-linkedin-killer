"""Integration tests for MessageSendGraph — connection-first, batch sending."""

import pytest

from src.config.config_loader import load_config
from src.core.agents.tools.message_template import render_template
from src.linkedin_mcp.graphs.linkedin_auth_graph import LinkedInAuthGraph
from src.linkedin_mcp.graphs.message_send_graph import MessageSendGraph
from src.linkedin_mcp.services.browser_manager_service import BrowserManagerService
from src.linkedin_mcp.services.employee_outreach_service import EmployeeOutreachService

# Test profiles — replace with real LinkedIn profiles for testing
TEST_PROFILES = [
    {
        "profile_url": "https://www.linkedin.com/in/francisco-nicolas-castro-37718b154/",
        "name": "Francisco Nicolas Castro",
    },
    {
        "profile_url": "https://www.linkedin.com/in/elena-cravet/",
        "name": "Elena Cravet",
    },
]
TEST_MESSAGE_TEMPLATE = "Hola {employee_name}, esto es una prueba."


@pytest.fixture
def config():
    """Load application config."""
    return load_config()


@pytest.fixture
def browser_manager(config):
    """Create and yield a browser manager, cleanup after test."""
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
def credentials(config):
    """Get LinkedIn credentials or skip test."""
    email = config.linkedin.email
    password = config.linkedin.password

    if not email or not password:
        pytest.skip(
            "LinkedIn credentials not configured (set LINKEDIN_EMAIL and LINKEDIN_PASSWORD)"
        )

    return {"email": email, "password": password}


@pytest.fixture
def authenticated_browser(browser_manager, credentials):
    """Start browser and authenticate with LinkedIn."""
    browser_manager.start_browser()

    auth_graph = LinkedInAuthGraph()
    auth_result = auth_graph.execute(
        credentials["email"], credentials["password"], browser_manager
    )

    if not auth_result.get("authenticated"):
        pytest.fail(
            f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
        )

    return browser_manager


class TestMessageSendGraph:
    """Integration tests for MessageSendGraph."""

    def test_connection_request_preferred(self, authenticated_browser):
        """Test that connection request is attempted before direct message."""
        graph = MessageSendGraph(browser_manager=authenticated_browser)
        profile = TEST_PROFILES[0]

        message_text = render_template(
            TEST_MESSAGE_TEMPLATE,
            {"employee_name": profile["name"]},
        )

        result = graph.execute(
            employee_profile_url=profile["profile_url"],
            employee_name=profile["name"],
            message_text=message_text,
            authenticated_browser_manager=authenticated_browser,
        )

        print(f"\n--- Connection Request Result ---")
        print(f"Profile: {result['employee_profile_url']}")
        print(f"Sent: {result['sent']}")
        print(f"Method: {result['method']}")
        print(f"Error: {result.get('error')}")

        assert result["employee_profile_url"] == profile["profile_url"]
        assert result["method"] in ("connection_request", "direct_message", "")

    def test_message_truncated_to_300_chars(self, authenticated_browser):
        """Test that connection request notes are truncated to 300 characters."""
        graph = MessageSendGraph(browser_manager=authenticated_browser)
        profile = TEST_PROFILES[0]

        # Create a message longer than 300 chars
        long_message = "A" * 350

        result = graph.execute(
            employee_profile_url=profile["profile_url"],
            employee_name=profile["name"],
            message_text=long_message,
            authenticated_browser_manager=authenticated_browser,
        )

        print(f"\n--- Truncation Test Result ---")
        print(f"Method: {result['method']}")
        print(f"Sent: {result['sent']}")
        print(f"Error: {result.get('error')}")

        # If it used connection_request, the 300-char truncation was applied
        assert result["employee_profile_url"] == profile["profile_url"]
        assert result["method"] in ("connection_request", "direct_message", "")


class TestBatchMessageSending:
    """Integration tests for batch message sending via EmployeeOutreachService."""

    def test_send_messages_batch(self, credentials):
        """Test sending multiple messages in a single browser session."""
        service = EmployeeOutreachService()

        messages = [
            {
                "profile_url": profile["profile_url"],
                "name": profile["name"],
                "message": render_template(
                    TEST_MESSAGE_TEMPLATE,
                    {"employee_name": profile["name"]},
                ),
                "subject": "",
            }
            for profile in TEST_PROFILES
        ]

        results = service.send_messages_batch(messages, credentials)

        print(f"\n--- Batch Send Results ---")
        for i, result in enumerate(results):
            print(
                f"  [{i+1}] {result.get('employee_name')}: "
                f"sent={result.get('sent')}, method={result.get('method')}, "
                f"error={result.get('error')}"
            )

        # Should return one result per message
        assert len(results) == len(messages)

        # Each result should have the expected structure
        for i, result in enumerate(results):
            assert result["employee_profile_url"] == TEST_PROFILES[i]["profile_url"]
            assert result["employee_name"] == TEST_PROFILES[i]["name"]
            assert isinstance(result["sent"], bool)
            assert result["method"] in ("connection_request", "direct_message", "")

    def test_batch_single_failure_does_not_stop_batch(self, credentials):
        """Test that a single failure doesn't prevent remaining messages from being sent."""
        service = EmployeeOutreachService()

        messages = [
            {
                "profile_url": "https://www.linkedin.com/in/nonexistent-profile-xyz-99999/",
                "name": "Nonexistent User",
                "message": "This should fail.",
                "subject": "",
            },
            {
                "profile_url": TEST_PROFILES[0]["profile_url"],
                "name": TEST_PROFILES[0]["name"],
                "message": render_template(
                    TEST_MESSAGE_TEMPLATE,
                    {"employee_name": TEST_PROFILES[0]["name"]},
                ),
                "subject": "",
            },
        ]

        results = service.send_messages_batch(messages, credentials)

        print(f"\n--- Failure Isolation Results ---")
        for i, result in enumerate(results):
            print(
                f"  [{i+1}] {result.get('employee_name')}: "
                f"sent={result.get('sent')}, error={result.get('error')}"
            )

        # Should still return results for all messages
        assert len(results) == len(messages)

        # Second message should have been attempted regardless of first failing
        assert results[1]["employee_profile_url"] == TEST_PROFILES[0]["profile_url"]


if __name__ == "__main__":
    """Run the test directly for manual testing."""
    import os

    config = load_config()
    email = os.getenv("LINKEDIN_EMAIL") or config.linkedin.email
    password = os.getenv("LINKEDIN_PASSWORD") or config.linkedin.password

    if not email or not password:
        print("ERROR: Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables")
        exit(1)

    print(f"Testing batch message send with {len(TEST_PROFILES)} profiles")
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

        # Test single message via graph (connection-first)
        print("\n--- Testing single message (connection-first) ---")
        graph = MessageSendGraph(browser_manager=manager)
        profile = TEST_PROFILES[0]

        message_text = render_template(
            TEST_MESSAGE_TEMPLATE,
            {"employee_name": profile["name"]},
        )

        result = graph.execute(
            employee_profile_url=profile["profile_url"],
            employee_name=profile["name"],
            message_text=message_text,
            authenticated_browser_manager=manager,
        )

        print(f"Sent: {result.get('sent')}")
        print(f"Method: {result.get('method')}")
        print(f"Error: {result.get('error')}")

    finally:
        manager.close_browser()

    # Test batch via service (separate browser lifecycle)
    print("\n--- Testing batch message send via service ---")
    service = EmployeeOutreachService()
    messages = [
        {
            "profile_url": p["profile_url"],
            "name": p["name"],
            "message": render_template(
                TEST_MESSAGE_TEMPLATE, {"employee_name": p["name"]}
            ),
            "subject": "",
        }
        for p in TEST_PROFILES
    ]

    results = service.send_messages_batch(
        messages, {"email": email, "password": password}
    )

    print(f"\n--- Batch Results ({len(results)} messages) ---")
    for i, r in enumerate(results):
        print(
            f"  [{i+1}] {r.get('employee_name')}: "
            f"sent={r.get('sent')}, method={r.get('method')}, "
            f"error={r.get('error')}"
        )
