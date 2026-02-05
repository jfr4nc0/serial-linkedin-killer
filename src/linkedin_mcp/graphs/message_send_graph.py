"""LangGraph workflow for sending a message or connection request to a LinkedIn user."""

from typing import Any, Dict, List, Optional, Tuple

from langgraph.graph import END, StateGraph
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.model.outreach_types import MessageResult, MessageSendState


class MessageSendGraph:
    """LangGraph workflow for sending a message or connection request on LinkedIn."""

    # Selectors for Connect button (direct)
    CONNECT_SELECTORS: List[Tuple[str, str]] = [
        # Priority 1: Anchor with "Invite ... to connect" aria-label (most reliable)
        (By.XPATH, "//a[contains(@aria-label, 'to connect')]"),
        # Priority 2: Anchor with href to custom-invite
        (By.XPATH, "//a[contains(@href, 'custom-invite')]"),
        # Priority 3: Anchor/button with Connect text and SVG icon
        (By.XPATH, "//*[self::a or self::button][.//svg[@id='connect-small']]"),
        # Priority 4: Button with aria-label
        (By.XPATH, "//button[contains(@aria-label, 'Connect')]"),
        # Fallback: Any element with Connect span
        (
            By.XPATH,
            "//*[self::button or self::a][.//span[normalize-space(text())='Connect']]",
        ),
    ]

    # Selectors for More dropdown -> Connect
    MORE_BUTTON_SELECTOR: Tuple[str, str] = (
        By.XPATH,
        "//button[contains(@aria-label, 'More')]",
    )
    MORE_CONNECT_SELECTOR: Tuple[str, str] = (
        By.XPATH,
        "//div[contains(@class, 'artdeco-dropdown__item')][.//span[text()='Connect']]",
    )

    # Selectors for Message button
    MESSAGE_SELECTORS: List[Tuple[str, str]] = [
        (By.XPATH, "//button[contains(@aria-label, 'Message')]"),
        (By.XPATH, "//button[.//span[normalize-space(text())='Message']]"),
        (By.XPATH, "//button[.//svg[contains(@id, 'message')]]"),
    ]

    # Selectors for "Add a note" button (inside modal dialog)
    ADD_NOTE_SELECTORS: List[Tuple[str, str]] = [
        # Priority 1: Scoped to modal with aria-label (most reliable)
        (
            By.CSS_SELECTOR,
            "div[role='dialog'] button[aria-label='Add a note'], .artdeco-modal button[aria-label='Add a note']",
        ),
        # XPath: button with exact aria-label
        (By.XPATH, "//button[@aria-label='Add a note']"),
        # XPath: button containing span with "Add a note" text
        (By.XPATH, "//button[.//span[contains(text(), 'Add a note')]]"),
        # XPath: secondary artdeco button in modal
        (
            By.XPATH,
            "//div[@role='dialog']//button[contains(@class, 'artdeco-button--secondary')]",
        ),
        # CSS: artdeco button with muted style
        (By.CSS_SELECTOR, "button.artdeco-button--muted.artdeco-button--secondary"),
        # CSS: ember button with mr1 class
        (By.CSS_SELECTOR, "button.ember-view.mr1"),
        # CSS: button inside modal actionbar
        (By.CSS_SELECTOR, ".artdeco-modal__actionbar button.artdeco-button--secondary"),
        # CSS: simple aria-label
        (By.CSS_SELECTOR, "button[aria-label='Add a note']"),
        # XPath: button with artdeco-button__text span
        (
            By.XPATH,
            "//button[.//span[@class='artdeco-button__text'][contains(., 'Add a note')]]",
        ),
    ]

    # Selectors for note textarea
    NOTE_TEXTAREA_SELECTORS: List[Tuple[str, str]] = [
        (By.CSS_SELECTOR, "textarea#custom-message"),
        (By.CSS_SELECTOR, "textarea[name='message']"),
        (By.XPATH, "//textarea[contains(@placeholder, 'Add a note')]"),
        (By.CSS_SELECTOR, "textarea"),
    ]

    # Selectors for Send invitation button
    SEND_INVITATION_SELECTORS: List[Tuple[str, str]] = [
        (By.XPATH, "//button[contains(@aria-label, 'Send invitation')]"),
        (By.XPATH, "//button[.//span[normalize-space(text())='Send']]"),
        (By.XPATH, "//button[contains(@aria-label, 'Send')]"),
        (By.XPATH, "//button[normalize-space(text())='Send']"),
    ]

    # Selectors for message text box
    MESSAGE_TEXTBOX_SELECTORS: List[Tuple[str, str]] = [
        (By.CSS_SELECTOR, ".msg-form__contenteditable"),
        (By.CSS_SELECTOR, "div[role='textbox']"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.XPATH, "//div[contains(@class, 'msg-form')]//div[@contenteditable='true']"),
    ]

    # Selectors for message send button
    MESSAGE_SEND_SELECTORS: List[Tuple[str, str]] = [
        (By.CSS_SELECTOR, "button.msg-form__send-button"),
        (By.XPATH, "//button[contains(@class, 'msg-form__send')]"),
        (By.XPATH, "//button[@type='submit'][.//span[text()='Send']]"),
        (By.XPATH, "//button[contains(@aria-label, 'Send')]"),
    ]

    def __init__(self, browser_manager: IBrowserManager):
        self.browser_manager = browser_manager
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(MessageSendState)

        workflow.add_node("navigate_to_profile", self._navigate_to_profile)
        workflow.add_node("detect_and_click", self._detect_and_click)
        workflow.add_node("send_direct_message", self._send_direct_message)
        workflow.add_node("send_connection_request", self._send_connection_request)

        workflow.set_entry_point("navigate_to_profile")
        workflow.add_edge("navigate_to_profile", "detect_and_click")

        workflow.add_conditional_edges(
            "detect_and_click",
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

    def _find_element_multi(
        self,
        driver: WebDriver,
        selectors: List[Tuple[str, str]],
        timeout: float = 5,
        clickable: bool = False,
    ) -> Optional[WebElement]:
        """Try multiple selectors, return first match or None."""
        for selector in selectors:
            try:
                condition = (
                    EC.element_to_be_clickable
                    if clickable
                    else EC.presence_of_element_located
                )
                return WebDriverWait(driver, timeout).until(condition(selector))
            except Exception:
                continue
        return None

    def _find_in_shadow_dom(
        self,
        driver: WebDriver,
        css_selector: str,
        shadow_host_selector: str = "#interop-outlet",
    ) -> Optional[WebElement]:
        """Find an element inside a shadow DOM."""
        try:
            return driver.execute_script(
                f"""
                const shadowHost = document.querySelector('{shadow_host_selector}');
                if (shadowHost && shadowHost.shadowRoot) {{
                    return shadowHost.shadowRoot.querySelector('{css_selector}');
                }}
                return null;
                """
            )
        except Exception:
            return None

    def _click_element(self, driver: WebDriver, element: WebElement) -> bool:
        """Try multiple strategies to click an element. Returns True if successful."""
        # Strategy 1: Scroll into view + JS click
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            pass

        # Strategy 2: Selenium native click
        try:
            element.click()
            return True
        except Exception:
            pass

        # Strategy 3: ActionChains click
        try:
            ActionChains(driver).move_to_element(element).click().perform()
            return True
        except Exception:
            pass

        # Strategy 4: JS click on parent button (if element is nested span/svg)
        try:
            parent = element.find_element(By.XPATH, "./ancestor::button")
            driver.execute_script("arguments[0].click();", parent)
            return True
        except Exception:
            pass

        # Strategy 5: Send Enter key
        try:
            element.send_keys("\n")
            return True
        except Exception:
            pass

        return False

    def _navigate_to_profile(self, state: MessageSendState) -> Dict[str, Any]:
        try:
            driver = state["browser_manager"].driver
            driver.get(state["employee_profile_url"])
            state["browser_manager"].random_delay(2, 3)
            return state
        except Exception as e:
            return {**state, "error": f"Failed to navigate to profile: {str(e)}"}

    def _detect_and_click(self, state: MessageSendState) -> Dict[str, Any]:
        """Detect and click the appropriate action button.

        Priority: Connect button > More dropdown -> Connect > Message button (fallback).
        Connection requests with a note are unlimited, while direct messages are limited.
        """
        if state.get("error"):
            return state

        try:
            driver = state["browser_manager"].driver

            # Try direct Connect buttons first
            connect_btn = self._find_element_multi(
                driver, self.CONNECT_SELECTORS, timeout=3
            )
            if connect_btn:
                if self._click_element(driver, connect_btn):
                    state["browser_manager"].random_delay(1, 2)
                    return {**state, "method": "connection_request"}

            # Try More dropdown -> Connect
            more_btn = self._find_element_multi(
                driver, [self.MORE_BUTTON_SELECTOR], timeout=2
            )
            if more_btn:
                if self._click_element(driver, more_btn):
                    state["browser_manager"].random_delay(0.5, 1)
                    connect_item = self._find_element_multi(
                        driver, [self.MORE_CONNECT_SELECTOR], timeout=2
                    )
                    if connect_item and self._click_element(driver, connect_item):
                        state["browser_manager"].random_delay(1, 2)
                        return {**state, "method": "connection_request"}

            # Fallback: Message button (already connected)
            msg_btn = self._find_element_multi(
                driver, self.MESSAGE_SELECTORS, timeout=2
            )
            if msg_btn:
                return {**state, "method": "direct_message"}

            return {**state, "error": "No Connect or Message button found"}

        except Exception as e:
            return {**state, "error": f"Failed to detect action: {str(e)}"}

    def _route_action(self, state: MessageSendState) -> str:
        if state.get("error"):
            return "skip"
        return state.get("method", "skip")

    def _send_direct_message(self, state: MessageSendState) -> Dict[str, Any]:
        """Send a direct message (for already-connected profiles)."""
        try:
            driver = state["browser_manager"].driver

            # Click Message button
            msg_button = self._find_element_multi(driver, self.MESSAGE_SELECTORS)
            if not msg_button:
                return {
                    **state,
                    "sent": False,
                    "error": "Could not find Message button",
                }

            if not self._click_element(driver, msg_button):
                return {
                    **state,
                    "sent": False,
                    "error": "Could not click Message button",
                }
            state["browser_manager"].random_delay(1, 2)

            # Find message text box
            text_box = self._find_element_multi(driver, self.MESSAGE_TEXTBOX_SELECTORS)
            if not text_box:
                return {
                    **state,
                    "sent": False,
                    "error": "Could not find message text box",
                }

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
                except Exception:
                    pass

            # Type message
            text_box.click()
            state["browser_manager"].random_delay(0.3, 0.5)
            text_box.send_keys(state["message_text"])
            state["browser_manager"].random_delay(0.5, 1)

            # Click send
            send_button = self._find_element_multi(driver, self.MESSAGE_SEND_SELECTORS)
            if not send_button:
                return {**state, "sent": False, "error": "Could not find Send button"}

            if not self._click_element(driver, send_button):
                return {**state, "sent": False, "error": "Could not click Send button"}
            state["browser_manager"].random_delay(1, 2)

            return {**state, "sent": True, "method": "direct_message"}

        except Exception as e:
            return {
                **state,
                "sent": False,
                "error": f"Failed to send message: {str(e)}",
            }

    def _send_connection_request(self, state: MessageSendState) -> Dict[str, Any]:
        """Complete the connection request dialog (Connect already clicked)."""
        try:
            driver = state["browser_manager"].driver

            state["browser_manager"].random_delay(1, 2)

            # Try multiple approaches to find and click "Add a note"
            add_note_btn = None

            # Approach 1: Shadow DOM query (LinkedIn uses shadow DOM for modals)
            try:
                add_note_btn = driver.execute_script(
                    """
                    const shadowHost = document.querySelector('#interop-outlet');
                    if (shadowHost && shadowHost.shadowRoot) {
                        return shadowHost.shadowRoot.querySelector('button[aria-label="Add a note"]') ||
                               shadowHost.shadowRoot.querySelector('button.artdeco-button--secondary') ||
                               Array.from(shadowHost.shadowRoot.querySelectorAll('button')).find(b => b.textContent.includes('Add a note'));
                    }
                    return null;
                """
                )
            except Exception:
                pass

            # Approach 2: Standard selectors fallback (for non-shadow DOM cases)
            if not add_note_btn:
                add_note_btn = self._find_element_multi(
                    driver, self.ADD_NOTE_SELECTORS, timeout=2, clickable=True
                )

            # Approach 3: JavaScript query on main DOM
            if not add_note_btn:
                try:
                    add_note_btn = driver.execute_script(
                        """
                        return document.querySelector('button[aria-label="Add a note"]') ||
                               document.querySelector('.artdeco-modal button.artdeco-button--secondary') ||
                               Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Add a note'));
                    """
                    )
                except Exception:
                    pass

            if not add_note_btn:
                return {
                    **state,
                    "sent": False,
                    "error": "Could not find 'Add a note' button",
                }

            if not self._click_element(driver, add_note_btn):
                return {
                    **state,
                    "sent": False,
                    "error": "Could not click 'Add a note' button",
                }
            state["browser_manager"].random_delay(0.5, 1)

            # Type note (300 char limit for connection requests)
            # Try shadow DOM first (LinkedIn uses #custom-message inside shadow DOM)
            state["browser_manager"].random_delay(0.5, 1)  # Wait for textarea to appear

            note_field = self._find_in_shadow_dom(
                driver,
                "#custom-message, div.connect-button-send-invite__custom-message-box, textarea[name='message'], textarea",
            )

            if not note_field:
                # Try direct JS query
                try:
                    note_field = driver.execute_script(
                        """
                        const shadowHost = document.querySelector('#interop-outlet');
                        if (shadowHost && shadowHost.shadowRoot) {
                            return shadowHost.shadowRoot.querySelector('#custom-message');
                        }
                        return null;
                    """
                    )
                except Exception:
                    pass

            if not note_field:
                note_field = self._find_element_multi(
                    driver, self.NOTE_TEXTAREA_SELECTORS
                )

            if not note_field:
                return {**state, "sent": False, "error": "Could not find note textarea"}

            # Click to focus (needed for contenteditable divs), then type
            note_field.click()
            state["browser_manager"].random_delay(0.2, 0.4)
            note_field.send_keys(state["message_text"][:300])
            state["browser_manager"].random_delay(0.5, 1)

            # Click Send invitation (try shadow DOM first)
            send_btn = self._find_in_shadow_dom(
                driver,
                "button[aria-label*='Send invitation'], button[aria-label*='Send now'], button.artdeco-button--primary, button.ml1",
            )
            # Fallback: find by text content in shadow DOM
            if not send_btn:
                try:
                    send_btn = driver.execute_script(
                        """
                        const shadowHost = document.querySelector('#interop-outlet');
                        if (shadowHost && shadowHost.shadowRoot) {
                            return Array.from(shadowHost.shadowRoot.querySelectorAll('button')).find(
                                b => b.textContent.trim() === 'Send' || b.textContent.includes('Send invitation')
                            );
                        }
                        return null;
                    """
                    )
                except Exception:
                    pass
            if not send_btn:
                send_btn = self._find_element_multi(
                    driver, self.SEND_INVITATION_SELECTORS, clickable=True
                )
            if not send_btn:
                return {**state, "sent": False, "error": "Could not find Send button"}

            if not self._click_element(driver, send_btn):
                return {**state, "sent": False, "error": "Could not click Send button"}
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
