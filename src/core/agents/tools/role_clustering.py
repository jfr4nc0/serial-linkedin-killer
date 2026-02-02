"""LLM-based role clustering for employee job titles."""

import json
import re
from collections import defaultdict
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.providers.llm_client import get_llm_client

ROLE_CATEGORIES = [
    "Engineering",
    "Finance",
    "Investment Banking / M&A",
    "Strategy Consulting",
    "Crypto / Web3",
    "Sales",
    "Marketing",
    "HR/People",
    "Operations",
    "Executive",
    "Other",
]

_CLASSIFICATION_PROMPT = """Classify each job title into exactly one of these categories:
{categories}

Job titles to classify:
{titles}

Respond with ONLY a JSON object mapping each title to its category. Example:
{{"Software Engineer": "Engineering", "CFO": "Executive", "Sales Manager": "Sales"}}

JSON response:"""


def cluster_employees_by_role(
    employees: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Cluster employees by role using LLM classification.

    Args:
        employees: List of employee dicts with at least 'title' field.

    Returns:
        Dict mapping role category to list of employees in that category.
    """
    if not employees:
        return {cat: [] for cat in ROLE_CATEGORIES}

    # Extract unique titles
    titles = list(
        {emp.get("title", "").strip() for emp in employees if emp.get("title")}
    )

    if not titles:
        return {"Other": employees}

    # Get classification from LLM
    title_to_category = _classify_titles_with_llm(titles)

    # Group employees by category
    clustered: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for emp in employees:
        title = emp.get("title", "").strip()
        category = title_to_category.get(title, "Other")
        clustered[category].append(emp)

    # Ensure all categories exist in output (empty lists for unused categories)
    result = {cat: clustered.get(cat, []) for cat in ROLE_CATEGORIES}

    # Log clustering summary
    summary = {cat: len(emps) for cat, emps in result.items() if emps}
    logger.info("Clustered employees by role", summary=summary, total=len(employees))

    return result


def _classify_titles_with_llm(titles: List[str]) -> Dict[str, str]:
    """Call LLM to classify job titles into categories.

    Args:
        titles: List of unique job titles.

    Returns:
        Dict mapping each title to its category.
    """
    if not titles:
        return {}

    # Build prompt
    categories_str = ", ".join(ROLE_CATEGORIES)
    titles_str = "\n".join(f"- {t}" for t in titles)
    prompt = _CLASSIFICATION_PROMPT.format(categories=categories_str, titles=titles_str)

    try:
        llm = get_llm_client()
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            logger.warning(
                "LLM response did not contain valid JSON", response=content[:500]
            )
            return {t: "Other" for t in titles}

        mapping = json.loads(json_match.group())

        # Validate categories
        validated = {}
        for title, category in mapping.items():
            if category in ROLE_CATEGORIES:
                validated[title] = category
            else:
                logger.debug(
                    "Invalid category from LLM, defaulting to Other",
                    title=title,
                    category=category,
                )
                validated[title] = "Other"

        # Add any missing titles as Other
        for title in titles:
            if title not in validated:
                validated[title] = "Other"

        return validated

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM response as JSON", error=str(e))
        return {t: "Other" for t in titles}
    except Exception as e:
        logger.exception("LLM classification failed", error=str(e))
        return {t: "Other" for t in titles}
