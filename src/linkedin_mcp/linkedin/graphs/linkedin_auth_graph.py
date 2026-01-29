from langgraph.graph import END, StateGraph
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from src.linkedin_mcp.linkedin.interfaces.services import IBrowserManager
from src.linkedin_mcp.linkedin.model.types import AuthState
from src.linkedin_mcp.linkedin.utils.profile_confirmation import profile_confirmation


class LinkedInAuthGraph:
    """LangGraph workflow for LinkedIn authentication."""

    def __init__(self):
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the authentication workflow graph."""
        workflow = StateGraph(AuthState)

        # Add nodes for authentication steps
        workflow.add_node("navigate_to_login", self._navigate_to_login)
        workflow.add_node("fill_credentials", self._fill_credentials)
        workflow.add_node("submit_login", self._submit_login)
        workflow.add_node("verify_authentication", self._verify_authentication)
        workflow.add_node("handle_captcha", self._handle_captcha)

        # Define the flow
        workflow.set_entry_point("navigate_to_login")
        workflow.add_edge("navigate_to_login", "fill_credentials")
        workflow.add_edge("fill_credentials", "submit_login")
        workflow.add_edge("submit_login", "verify_authentication")

        # Conditional edge from verify_authentication
        workflow.add_conditional_edges(
            "verify_authentication",
            self._should_handle_captcha,
            {"captcha": "handle_captcha", "complete": END},
        )

        # After handling CAPTCHA, go back to verify authentication
        workflow.add_edge("handle_captcha", "verify_authentication")

        return workflow.compile()

    def _navigate_to_login(self, state: AuthState) -> AuthState:
        """Navigate to LinkedIn jobs page."""
        try:
            driver = state["browser_manager"].driver
            driver.get("https://www.linkedin.com/jobs/")
            state["browser_manager"].random_delay(2, 4)
            return state
        except Exception as e:
            state["error"] = f"Failed to navigate to LinkedIn: {str(e)}"
            return state

    def _fill_credentials(self, state: AuthState) -> AuthState:
        """Fill email and password fields."""
        try:
            browser_manager = state["browser_manager"]

            # Wait for and fill email field
            email_field = browser_manager.wait_for_element(By.ID, "session_key")
            email_field.clear()
            email_field.send_keys(state["email"])
            browser_manager.random_delay(1, 2)

            # Wait for and fill password field
            password_field = browser_manager.wait_for_element(By.ID, "session_password")
            password_field.clear()
            password_field.send_keys(state["password"])
            browser_manager.random_delay(1, 2)

            return state

        except TimeoutException:
            state["error"] = "Login form not found - page structure may have changed"
            return state
        except Exception as e:
            state["error"] = f"Failed to fill credentials: {str(e)}"
            return state

    def _submit_login(self, state: AuthState) -> AuthState:
        """Click the Sign In button."""
        try:
            browser_manager = state["browser_manager"]

            # Find and click the Sign In button
            sign_in_btn = browser_manager.wait_for_clickable(
                By.CSS_SELECTOR, 'button[data-id="sign-in-form__submit-btn"]'
            )
            sign_in_btn.click()
            browser_manager.random_delay(3, 5)

            return state

        except TimeoutException:
            state["error"] = "Sign In button not found"
            return state
        except Exception as e:
            state["error"] = f"Failed to submit login: {str(e)}"
            return state

    def _verify_authentication(self, state: AuthState) -> AuthState:
        """Verify that authentication was successful or detect CAPTCHA."""
        try:
            driver = state["browser_manager"].driver
            current_url = driver.current_url

            # Check for CAPTCHA challenge
            if "/checkpoint/challenge" in current_url:
                state["captcha_detected"] = True
                state["authenticated"] = False
                print(f"\n🔒 CAPTCHA Challenge Detected!")
                print(f"Current URL: {current_url}")
                return state

            # Check if we're redirected away from login page (successful authentication)
            if "/jobs/" in current_url and "/login" not in current_url:
                state["authenticated"] = True
                state["captcha_detected"] = False
            else:
                state["authenticated"] = False
                state["captcha_detected"] = False
                state["error"] = "Login failed - still on login page"

            return state

        except Exception as e:
            state["authenticated"] = False
            state["captcha_detected"] = False
            state["error"] = f"Authentication verification error: {str(e)}"
            return state

    def _should_handle_captcha(self, state: AuthState) -> str:
        """Determine if CAPTCHA handling is needed."""
        if state.get("captcha_detected", False) and not state.get(
            "captcha_solved", False
        ):
            return "captcha"
        else:
            return "complete"

    def _handle_captcha(self, state: AuthState) -> AuthState:
        """Handle CAPTCHA challenge by waiting for user to solve it manually."""
        try:
            driver = state["browser_manager"].driver
            current_url = driver.current_url

            print(f"\n" + "=" * 60)
            print(f"🔒 CAPTCHA CHALLENGE DETECTED")
            print(f"=" * 60)
            print(f"Current URL: {current_url}")
            print(f"\n📋 INSTRUCTIONS:")
            print(f"1. Look at the browser window - LinkedIn is showing a CAPTCHA")
            print(f"2. Manually solve the CAPTCHA challenge")
            print(f"3. Complete any additional verification steps")
            print(f"4. When you see the LinkedIn homepage/jobs page, come back here")
            print(f"\n⏳ The automation will wait for your confirmation...")
            print(f"=" * 60)

            # Wait for user confirmation
            input(
                "\n✅ Press ENTER after you have successfully solved the CAPTCHA and are logged in: "
            )

            # Add a small delay to let the page stabilize
            state["browser_manager"].random_delay(2, 3)

            # Mark CAPTCHA as solved
            state["captcha_solved"] = True
            state["captcha_detected"] = False

            print(
                f"✅ CAPTCHA handling completed. Continuing authentication verification..."
            )

            return state

        except KeyboardInterrupt:
            state["error"] = "CAPTCHA handling cancelled by user"
            state["authenticated"] = False
            return state
        except Exception as e:
            state["error"] = f"Error during CAPTCHA handling: {str(e)}"
            state["authenticated"] = False
            return state

    def execute(
        self, email: str, password: str, browser_manager: "IBrowserManager"
    ) -> AuthState:
        """Execute the authentication workflow."""
        initial_state = AuthState(
            email=email,
            password=password,
            browser_manager=browser_manager,
            authenticated=False,
            captcha_detected=False,
            captcha_solved=False,
            error="",
        )

        result = self.graph.invoke(initial_state)
        return result
