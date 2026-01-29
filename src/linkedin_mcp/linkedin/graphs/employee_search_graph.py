"""LangGraph workflow for searching employees at a LinkedIn company page."""

from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.linkedin_mcp.linkedin.interfaces.services import IBrowserManager
from src.linkedin_mcp.linkedin.model.outreach_types import (
    EmployeeResult,
    EmployeeSearchState,
)


class EmployeeSearchGraph:
    """LangGraph workflow for searching employees on a LinkedIn company page."""

    def __init__(self, browser_manager: IBrowserManager):
        self.browser_manager = browser_manager
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(EmployeeSearchState)

        workflow.add_node("navigate_to_people", self._navigate_to_people)
        workflow.add_node("extract_employees", self._extract_employees)
        workflow.add_node("check_pagination", self._check_pagination)
        workflow.add_node("navigate_next_page", self._navigate_next_page)

        workflow.set_entry_point("navigate_to_people")
        workflow.add_edge("navigate_to_people", "extract_employees")
        workflow.add_edge("extract_employees", "check_pagination")

        workflow.add_conditional_edges(
            "check_pagination",
            self._should_continue,
            {"continue": "navigate_next_page", "finish": END},
        )

        workflow.add_edge("navigate_next_page", "extract_employees")

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
            state["browser_manager"].driver.get(people_url)
            state["browser_manager"].random_delay(1, 2)

            return {**state, "current_page": 1}

        except Exception as e:
            return {
                **state,
                "errors": state["errors"]
                + [f"Failed to navigate to people page: {str(e)}"],
            }

    def _extract_employees(self, state: EmployeeSearchState) -> Dict[str, Any]:
        """Extract employee cards from the current page."""
        try:
            driver = state["browser_manager"].driver
            page_employees = []

            # Wait for employee cards to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".org-people-profile-card, .artdeco-list__item",
                        )
                    )
                )
            except Exception:
                return {
                    **state,
                    "errors": state["errors"] + ["No employee cards found on page"],
                }

            cards = driver.find_elements(
                By.CSS_SELECTOR,
                ".org-people-profile-card, .artdeco-list__item",
            )

            for card in cards:
                if (
                    len(state["collected_employees"]) + len(page_employees)
                    >= state["limit"]
                ):
                    break

                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        card,
                    )
                    state["browser_manager"].random_delay(0.2, 0.4)

                    # Extract name
                    try:
                        name_el = card.find_element(
                            By.CSS_SELECTOR,
                            ".org-people-profile-card__profile-title, .artdeco-entity-lockup__title",
                        )
                        name = name_el.text.strip()
                    except NoSuchElementException:
                        continue

                    # Extract title
                    try:
                        title_el = card.find_element(
                            By.CSS_SELECTOR,
                            ".org-people-profile-card__profile-info, .artdeco-entity-lockup__subtitle",
                        )
                        title = title_el.text.strip()
                    except NoSuchElementException:
                        title = ""

                    # Extract profile URL
                    try:
                        link_el = card.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
                        profile_url = link_el.get_attribute("href")
                    except NoSuchElementException:
                        continue

                    if name and profile_url:
                        page_employees.append(
                            EmployeeResult(
                                name=name,
                                title=title,
                                profile_url=profile_url,
                            )
                        )

                except Exception:
                    continue

            return {
                **state,
                "collected_employees": state["collected_employees"] + page_employees,
            }

        except Exception as e:
            return {
                **state,
                "errors": state["errors"] + [f"Failed to extract employees: {str(e)}"],
            }

    def _check_pagination(self, state: EmployeeSearchState) -> Dict[str, Any]:
        return state

    def _should_continue(self, state: EmployeeSearchState) -> str:
        if len(state["collected_employees"]) >= state["limit"]:
            return "finish"

        if state["current_page"] >= 10:
            return "finish"

        try:
            driver = state["browser_manager"].driver
            next_button = driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Next'], .artdeco-pagination__button--next",
            )
            if next_button.is_enabled() and not next_button.get_attribute("disabled"):
                return "continue"
        except NoSuchElementException:
            pass

        return "finish"

    def _navigate_next_page(self, state: EmployeeSearchState) -> Dict[str, Any]:
        try:
            driver = state["browser_manager"].driver
            next_button = driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Next'], .artdeco-pagination__button--next",
            )
            next_button.click()

            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".org-people-profile-card, .artdeco-list__item")
                )
            )
            state["browser_manager"].random_delay(0.5, 1)

            return {**state, "current_page": state["current_page"] + 1}

        except Exception as e:
            return {
                **state,
                "errors": state["errors"]
                + [f"Failed to navigate to next page: {str(e)}"],
            }

    def execute(
        self,
        company_linkedin_url: str,
        company_name: str,
        limit: int,
        authenticated_browser_manager: IBrowserManager,
    ) -> List[EmployeeResult]:
        """Execute the employee search workflow with pre-authenticated browser."""
        initial_state = EmployeeSearchState(
            company_linkedin_url=company_linkedin_url,
            company_name=company_name,
            browser_manager=authenticated_browser_manager,
            collected_employees=[],
            current_page=1,
            limit=limit,
            errors=[],
        )

        result = self.graph.invoke(initial_state)
        return result["collected_employees"]
