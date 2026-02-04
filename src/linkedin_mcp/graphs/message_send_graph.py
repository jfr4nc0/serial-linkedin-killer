"""LangGraph workflow for sending a message or connection request to a LinkedIn user."""

from typing import Any, Dict

from langgraph.graph import END, StateGraph
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.model.outreach_types import MessageResult, MessageSendState


class MessageSendGraph:
    """LangGraph workflow for sending a message or connection request on LinkedIn."""

    def __init__(self, browser_manager: IBrowserManager):
        self.browser_manager = browser_manager
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(MessageSendState)

        workflow.add_node("navigate_to_profile", self._navigate_to_profile)
        workflow.add_node("detect_action", self._detect_action)
        workflow.add_node("send_direct_message", self._send_direct_message)
        workflow.add_node("send_connection_request", self._send_connection_request)

        workflow.set_entry_point("navigate_to_profile")
        workflow.add_edge("navigate_to_profile", "detect_action")

        workflow.add_conditional_edges(
            "detect_action",
            self._route_action,
            {
                "direct_message": "send_direct_message",
                "connection_request": "send_connection_request",
                "skip": END,
            },
        )

        workflow.add_edge("send_direct_message", END)
        workflow.add_edge("send_connection_request", END)

        return workflow.compile()

    def _navigate_to_profile(self, state: MessageSendState) -> Dict[str, Any]:
        try:
            driver = state["browser_manager"].driver
            driver.get(state["employee_profile_url"])
            state["browser_manager"].random_delay(1, 2)

            # Wait for profile to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".pv-top-card, .scaffold-layout")
                )
            )

            return state

        except Exception as e:
            return {**state, "error": f"Failed to navigate to profile: {str(e)}"}

    def _detect_action(self, state: MessageSendState) -> Dict[str, Any]:
        """Detect whether Message or Connect button is available."""
        if state.get("error"):
            return state

        try:
            driver = state["browser_manager"].driver

            # Check for Message button
            try:
                driver.find_element(
                    By.XPATH, "//button[contains(@aria-label, 'Message')]"
                )
                return {**state, "method": "direct_message"}
            except NoSuchElementException:
                pass

            # Check for Connect button
            try:
                driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Connect') or contains(@aria-label, 'connect')]",
                )
                return {**state, "method": "connection_request"}
            except NoSuchElementException:
                pass

            # Check More button dropdown for Connect
            try:
                more_button = driver.find_element(
                    By.XPATH, "//button[contains(@aria-label, 'More actions')]"
                )
                more_button.click()
                state["browser_manager"].random_delay(0.5, 1)

                driver.find_element(
                    By.XPATH,
                    "//span[text()='Connect']/ancestor::button | //div[contains(@class, 'artdeco-dropdown__item')][.//span[text()='Connect']]",
                )
                return {**state, "method": "connection_request"}
            except NoSuchElementException:
                pass

            return {**state, "error": "No Message or Connect button found"}

        except Exception as e:
            return {**state, "error": f"Failed to detect action: {str(e)}"}

    def _route_action(self, state: MessageSendState) -> str:
        if state.get("error"):
            return "skip"
        return state.get("method", "skip")

    def _send_direct_message(self, state: MessageSendState) -> Dict[str, Any]:
        try:
            driver = state["browser_manager"].driver

            # Click Message button — use JS click to bypass interactability issues
            msg_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@aria-label, 'Message')]")
                )
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", msg_button
            )
            state["browser_manager"].random_delay(0.3, 0.5)
            # Use JS click — bypasses Selenium's interactability check
            driver.execute_script("arguments[0].click();", msg_button)
            state["browser_manager"].random_delay(1, 2)

            # Wait for message dialog
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".msg-form__contenteditable, div[role='textbox']")
                )
            )

            # Fill in subject field if provided
            subject = state.get("subject", "")
            if subject:
                try:
                    subject_input = driver.find_element(
                        By.CSS_SELECTOR,
                        "input[name='subject'], input[placeholder*='Subject']",
                    )
                    subject_input.clear()
                    subject_input.send_keys(subject)
                    state["browser_manager"].random_delay(0.3, 0.5)
                except NoSuchElementException:
                    # Subject field not present (some LinkedIn message dialogs don't have it)
                    pass

            # Type message
            text_box = driver.find_element(
                By.CSS_SELECTOR, ".msg-form__contenteditable, div[role='textbox']"
            )
            text_box.click()
            state["browser_manager"].random_delay(0.3, 0.5)
            text_box.send_keys(state["message_text"])
            state["browser_manager"].random_delay(0.5, 1)

            # Click send
            send_button = driver.find_element(
                By.CSS_SELECTOR, "button.msg-form__send-button, button[type='submit']"
            )
            send_button.click()
            state["browser_manager"].random_delay(1, 2)

            return {**state, "sent": True, "method": "direct_message"}

        except Exception as e:
            return {
                **state,
                "sent": False,
                "error": f"Failed to send message: {str(e)}",
            }

    def _send_connection_request(self, state: MessageSendState) -> Dict[str, Any]:
        try:
            driver = state["browser_manager"].driver

            # Click Connect button (may be in dropdown or main actions)
            try:
                connect_button = driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Connect') or contains(@aria-label, 'connect')]",
                )
                connect_button.click()
            except NoSuchElementException:
                # Try from dropdown (already open from detect_action)
                connect_item = driver.find_element(
                    By.XPATH,
                    "//span[text()='Connect']/ancestor::button | //div[contains(@class, 'artdeco-dropdown__item')][.//span[text()='Connect']]",
                )
                connect_item.click()

            state["browser_manager"].random_delay(1, 2)

            # Click "Add a note" button
            try:
                add_note_button = driver.find_element(
                    By.XPATH, "//button[contains(@aria-label, 'Add a note')]"
                )
                add_note_button.click()
                state["browser_manager"].random_delay(0.5, 1)

                # Type note (300 char limit for connection requests)
                note_text = state["message_text"][:300]
                note_field = driver.find_element(
                    By.CSS_SELECTOR, "textarea[name='message'], textarea#custom-message"
                )
                note_field.send_keys(note_text)
                state["browser_manager"].random_delay(0.5, 1)

                # Click Send
                send_button = driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Send') or @aria-label='Send now']",
                )
                send_button.click()

            except NoSuchElementException:
                # No "Add a note" - just send without note
                try:
                    send_button = driver.find_element(
                        By.XPATH,
                        "//button[contains(@aria-label, 'Send') or @aria-label='Send now']",
                    )
                    send_button.click()
                except NoSuchElementException:
                    pass

            state["browser_manager"].random_delay(1, 2)

            return {**state, "sent": True, "method": "connection_request"}

        except Exception as e:
            return {
                **state,
                "sent": False,
                "error": f"Failed to send connection request: {str(e)}",
            }

    def execute(
        self,
        employee_profile_url: str,
        employee_name: str,
        message_text: str,
        authenticated_browser_manager: IBrowserManager,
        subject: str = "",
    ) -> MessageResult:
        """Execute the message send workflow."""
        initial_state = MessageSendState(
            employee_profile_url=employee_profile_url,
            employee_name=employee_name,
            message_text=message_text,
            subject=subject,
            browser_manager=authenticated_browser_manager,
            sent=False,
            method="",
            error="",
        )

        result = self.graph.invoke(initial_state)

        return MessageResult(
            employee_profile_url=result.get("employee_profile_url", ""),
            employee_name=result.get("employee_name", ""),
            sent=result.get("sent", False),
            method=result.get("method", ""),
            error=result.get("error"),
        )
