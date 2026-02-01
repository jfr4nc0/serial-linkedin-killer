"""LangGraph workflow for searching employees at a LinkedIn company page."""

from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from selenium.webdriver.support.ui import WebDriverWait

from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.model.outreach_types import EmployeeResult, EmployeeSearchState
from src.linkedin_mcp.utils.linkedin_selectors import (
    LinkedInEmployeeSelectors,
    SelectorFailure,
    clean_profile_url,
    extract_name_from_element,
)
from src.linkedin_mcp.utils.logging_config import get_mcp_logger

logger = get_mcp_logger()


class EmployeeSearchGraph:
    """LangGraph workflow for searching employees on a LinkedIn company page."""

    MAX_SHOW_MORE_CLICKS = 20

    def __init__(self, browser_manager: IBrowserManager):
        self.browser_manager = browser_manager
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(EmployeeSearchState)

        workflow.add_node("navigate_to_people", self._navigate_to_people)
        workflow.add_node("extract_employees", self._extract_employees)
        workflow.add_node("load_more", self._load_more)

        workflow.set_entry_point("navigate_to_people")
        workflow.add_edge("navigate_to_people", "extract_employees")

        workflow.add_conditional_edges(
            "extract_employees",
            self._should_load_more,
            {"load_more": "load_more", "finish": END},
        )

        workflow.add_edge("load_more", "extract_employees")

        return workflow.compile()

    def _navigate_to_people(self, state: EmployeeSearchState) -> Dict[str, Any]:
        """Navigate to the company's people page."""
        try:
            url = state["company_linkedin_url"].rstrip("/")
            if not url.startswith("https://"):
                url = (
                    f"https://www.{url}"
                    if not url.startswith("www.")
                    else f"https://{url}"
                )

            people_url = f"{url}/people/"
            logger.info(f"Navigating to {people_url}")
            state["browser_manager"].driver.get(people_url)
            # Wait for page load — just enough for DOM to be ready
            state["browser_manager"].random_delay(0.5, 1)

            return {}

        except Exception as e:
            return {
                "errors": state["errors"]
                + [f"Failed to navigate to people page: {str(e)}"],
            }

    def _extract_employees(self, state: EmployeeSearchState) -> Dict[str, Any]:
        """Extract employee cards from currently visible cards."""
        try:
            driver = state["browser_manager"].driver
            extracted_urls = state["extracted_urls"]
            new_employees = []

            # Wait for cards to be present
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: LinkedInEmployeeSelectors.CARD.find_elements(d)
                )
            except Exception:
                logger.warning("No employee cards found on page")
                return {
                    "errors": state["errors"] + ["No employee cards found on page"],
                }

            cards = LinkedInEmployeeSelectors.CARD.find_elements(driver)
            logger.info(
                f"Found {len(cards)} total cards, {len(extracted_urls)} already extracted"
            )

            # Scroll to bottom of the cards section in one go to ensure
            # all card DOM content is rendered (avoids per-card scrolling)
            if cards:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end'});",
                    cards[-1],
                )
                state["browser_manager"].random_delay(0.1, 0.3)

            for card in cards:
                if (
                    len(state["collected_employees"]) + len(new_employees)
                    >= state["limit"]
                ):
                    break

                try:
                    # Extract profile URL first to check for duplicates
                    try:
                        link_el = LinkedInEmployeeSelectors.PROFILE_URL.find_element(
                            card
                        )
                        profile_url = clean_profile_url(link_el.get_attribute("href"))
                    except SelectorFailure:
                        continue

                    if profile_url in extracted_urls:
                        continue

                    # Extract name
                    try:
                        name_el = LinkedInEmployeeSelectors.NAME.find_element(card)
                        name = extract_name_from_element(name_el)
                    except SelectorFailure as e:
                        logger.debug(f"Name extraction failed: {e}")
                        continue

                    if not name:
                        continue

                    # Extract title (optional)
                    title = ""
                    try:
                        title_el = LinkedInEmployeeSelectors.TITLE.find_element(card)
                        if title_el:
                            title = title_el.text.strip()
                    except SelectorFailure:
                        pass

                    extracted_urls.add(profile_url)
                    new_employees.append(
                        EmployeeResult(
                            name=name,
                            title=title,
                            profile_url=profile_url,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Card extraction error: {e}")
                    continue

            logger.info(
                f"Extracted {len(new_employees)} new employees "
                f"(total: {len(state['collected_employees']) + len(new_employees)})"
            )

            return {
                "collected_employees": state["collected_employees"] + new_employees,
                "extracted_urls": extracted_urls,
            }

        except Exception as e:
            return {
                "errors": state["errors"] + [f"Failed to extract employees: {str(e)}"],
            }

    def _should_load_more(self, state: EmployeeSearchState) -> str:
        """Check if we need to load more results."""
        if len(state["collected_employees"]) >= state["limit"]:
            logger.info(
                f"Limit reached: {len(state['collected_employees'])}/{state['limit']}"
            )
            return "finish"

        try:
            driver = state["browser_manager"].driver
            show_more = LinkedInEmployeeSelectors.SHOW_MORE.find_element(driver)
            if show_more and show_more.is_displayed() and show_more.is_enabled():
                return "load_more"
        except (SelectorFailure, Exception):
            pass

        logger.info("No more results to load")
        return "finish"

    def _load_more(self, state: EmployeeSearchState) -> Dict[str, Any]:
        """Click 'Show more results' button and wait for new cards."""
        try:
            driver = state["browser_manager"].driver
            cards_before = len(LinkedInEmployeeSelectors.CARD.find_elements(driver))

            show_more = LinkedInEmployeeSelectors.SHOW_MORE.find_element(driver)
            # Use JS click — faster than scrolling into view + selenium click
            driver.execute_script("arguments[0].click();", show_more)

            # Wait for new cards to appear
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: len(LinkedInEmployeeSelectors.CARD.find_elements(d))
                    > cards_before
                )
            except Exception:
                logger.warning("No new cards loaded after clicking Show more")

            state["browser_manager"].random_delay(0.3, 0.5)
            return {}

        except Exception as e:
            return {
                "errors": state["errors"] + [f"Failed to load more results: {str(e)}"],
            }

    def execute(
        self,
        company_linkedin_url: str,
        company_name: str,
        limit: int,
        authenticated_browser_manager: IBrowserManager,
    ) -> List[EmployeeResult]:
        """Execute the employee search workflow with pre-authenticated browser."""
        logger.info(f"Starting employee search for {company_name} (limit: {limit})")

        initial_state = EmployeeSearchState(
            company_linkedin_url=company_linkedin_url,
            company_name=company_name,
            browser_manager=authenticated_browser_manager,
            collected_employees=[],
            extracted_urls=set(),
            limit=limit,
            errors=[],
        )

        result = self.graph.invoke(initial_state)

        if result.get("errors"):
            logger.warning(f"Employee search completed with errors: {result['errors']}")

        logger.info(
            f"Employee search for {company_name} completed: "
            f"{len(result['collected_employees'])} employees found"
        )

        return result["collected_employees"]
