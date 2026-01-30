"""Multi-strategy CSS/XPath selectors for LinkedIn page scraping.

Provides fallback selector strategies that try multiple approaches
to find elements, making the scraper resilient to LinkedIn UI changes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


class SelectorType(Enum):
    CSS = "css"
    XPATH = "xpath"


class SelectorFailure(Exception):
    """Raised when all selector strategies fail for a required element."""

    def __init__(self, selector_name: str, attempts: List[str]):
        self.selector_name = selector_name
        self.attempts = attempts
        super().__init__(
            f"Failed to find '{selector_name}'. "
            f"Tried {len(attempts)} strategies: {'; '.join(attempts)}"
        )


@dataclass
class SelectorStrategy:
    """A single selector with type and description."""

    selector: str
    selector_type: SelectorType
    description: str = ""

    @property
    def by(self) -> str:
        return {
            SelectorType.CSS: By.CSS_SELECTOR,
            SelectorType.XPATH: By.XPATH,
        }[self.selector_type]

    def find_element(self, parent: Any) -> Any:
        return parent.find_element(self.by, self.selector)

    def find_elements(self, parent: Any) -> List[Any]:
        return parent.find_elements(self.by, self.selector)


@dataclass
class MultiStrategySelector:
    """Multiple selector strategies with ordered fallback."""

    name: str
    strategies: List[SelectorStrategy] = field(default_factory=list)
    required: bool = True

    def find_element(self, parent: Any) -> Optional[Any]:
        """Try each strategy in order, return first match."""
        errors = []
        for strategy in self.strategies:
            try:
                el = strategy.find_element(parent)
                if el:
                    return el
            except (NoSuchElementException, Exception) as e:
                errors.append(f"{strategy.description}: {type(e).__name__}")

        if self.required:
            raise SelectorFailure(self.name, errors)
        return None

    def find_elements(self, parent: Any) -> List[Any]:
        """Try each strategy in order, return first non-empty result."""
        for strategy in self.strategies:
            try:
                elements = strategy.find_elements(parent)
                if elements:
                    return elements
            except Exception:
                continue
        return []


class LinkedInEmployeeSelectors:
    """Verified selectors for LinkedIn company /people/ page."""

    # Employee card container
    CARD = MultiStrategySelector(
        name="employee_card",
        strategies=[
            SelectorStrategy(
                "li.org-people-profile-card__profile-card-spacing",
                SelectorType.CSS,
                "profile card li",
            ),
            SelectorStrategy(
                "li.org-people-profile-card",
                SelectorType.CSS,
                "org-people-profile-card li",
            ),
            SelectorStrategy(
                "//li[contains(@class, 'org-people-profile-card')]",
                SelectorType.XPATH,
                "XPath: li with org-people-profile-card class",
            ),
        ],
    )

    # Employee name - extract from link's aria-label or inner text
    NAME = MultiStrategySelector(
        name="employee_name",
        strategies=[
            SelectorStrategy(
                ".artdeco-entity-lockup__title a[data-test-app-aware-link]",
                SelectorType.CSS,
                "artdeco title link with data-test attr",
            ),
            SelectorStrategy(
                ".artdeco-entity-lockup__title a[href*='/in/']",
                SelectorType.CSS,
                "artdeco title link with /in/ href",
            ),
            SelectorStrategy(
                ".org-people-profile-card__profile-title",
                SelectorType.CSS,
                "org profile title class",
            ),
            SelectorStrategy(
                ".//div[contains(@class, 'artdeco-entity-lockup__title')]//a",
                SelectorType.XPATH,
                "XPath: title lockup link",
            ),
        ],
    )

    # Employee job title
    TITLE = MultiStrategySelector(
        name="employee_title",
        strategies=[
            SelectorStrategy(
                ".artdeco-entity-lockup__subtitle div.lt-line-clamp",
                SelectorType.CSS,
                "subtitle lt-line-clamp div",
            ),
            SelectorStrategy(
                ".artdeco-entity-lockup__subtitle",
                SelectorType.CSS,
                "artdeco subtitle",
            ),
            SelectorStrategy(
                ".org-people-profile-card__profile-info div.lt-line-clamp",
                SelectorType.CSS,
                "profile-info lt-line-clamp",
            ),
        ],
        required=False,
    )

    # Profile URL link
    PROFILE_URL = MultiStrategySelector(
        name="profile_url",
        strategies=[
            SelectorStrategy(
                ".artdeco-entity-lockup__title a[href*='/in/']",
                SelectorType.CSS,
                "title link with /in/ href",
            ),
            SelectorStrategy(
                "a[href*='/in/']",
                SelectorType.CSS,
                "any link with /in/ href",
            ),
        ],
    )

    # "Show more results" button (replaces pagination)
    SHOW_MORE = MultiStrategySelector(
        name="show_more_button",
        strategies=[
            SelectorStrategy(
                "button.scaffold-finite-scroll__load-button",
                SelectorType.CSS,
                "scaffold load button",
            ),
            SelectorStrategy(
                "//button[contains(@class, 'scaffold-finite-scroll__load-button')]",
                SelectorType.XPATH,
                "XPath: scaffold load button",
            ),
            SelectorStrategy(
                "//button[contains(., 'Show more')]",
                SelectorType.XPATH,
                "XPath: button with Show more text",
            ),
        ],
        required=False,
    )


def extract_name_from_element(name_element: Any) -> str:
    """Extract employee name from the name link element.

    Tries aria-label first ("View {Name}'s profile"), then falls back to text.
    """
    aria_label = name_element.get_attribute("aria-label")
    if (
        aria_label
        and aria_label.startswith("View ")
        and aria_label.endswith("'s profile")
    ):
        return aria_label[5:-10].strip()

    # Fallback: get inner text
    text = name_element.text.strip()
    if text:
        return text

    # Fallback: find inner div text
    try:
        inner = name_element.find_element(By.CSS_SELECTOR, "div.lt-line-clamp")
        return inner.text.strip()
    except NoSuchElementException:
        return ""


def clean_profile_url(url: str) -> str:
    """Clean LinkedIn profile URL by removing query parameters."""
    if not url:
        return ""
    return url.split("?")[0]
