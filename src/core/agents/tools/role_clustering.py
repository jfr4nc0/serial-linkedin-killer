"""LLM-based role clustering for employee job titles."""

import json
import re
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.providers.llm_client import get_llm_client

ROLE_CATEGORIES = [
    "Engineering",
    "Finance",
    "Investment Banking / M&A",
    "Strategy Consulting",
    "Crypto / Web3",
    "Broker_Exchange_HeadOfProduct",
    "WealthManager_PortfolioManager",
    "Fintech_ProductManager",
    "FamilyOffice_CIO",
    "Insurance_HeadOfProduct",
    "Corporate_Treasurer_CFO",
    "Boutique_FundManager",
    "Sales",
    "Marketing",
    "HR/People",
    "Operations",
    "Executive",
    "Other",
]

B2C_ROLES = {
    "Finance",
    "Engineering",
    "Investment Banking / M&A",
    "Strategy Consulting",
    "Crypto / Web3",
}

B2B_ROLES = {
    "Broker_Exchange_HeadOfProduct",
    "WealthManager_PortfolioManager",
    "Fintech_ProductManager",
    "FamilyOffice_CIO",
    "Insurance_HeadOfProduct",
    "Corporate_Treasurer_CFO",
    "Boutique_FundManager",
}

_CLASSIFICATION_PROMPT = """Classify each job title into exactly one of these categories:
{categories}

Category guidance:
- B2B / institutional roles (classify by the type of company and seniority):
  - "Broker_Exchange_HeadOfProduct": Head of Product, Product Director, or similar at brokers, exchanges, or trading platforms.
  - "WealthManager_PortfolioManager": Portfolio managers, wealth advisors, or investment managers at ALyCs, wealth management firms, or RIAs.
  - "Fintech_ProductManager": Product managers or product leads at fintech companies, neobanks, or digital wallets.
  - "FamilyOffice_CIO": CIO, investment director, or senior investment roles at family offices.
  - "Insurance_HeadOfProduct": Head of Product, product director, or actuarial leads at insurance companies (especially life/savings products).
  - "Corporate_Treasurer_CFO": Corporate treasurers, CFOs, or heads of treasury at non-financial corporations.
  - "Boutique_FundManager": Fund managers, portfolio managers, or partners at boutique/independent asset management firms or hedge funds.
- B2C / individual professional roles:
  - "Finance": Finance professionals (analysts, accountants, controllers) NOT covered by the B2B categories above.
  - "Engineering": Software engineers, developers, data engineers, ML engineers, DevOps.
  - "Investment Banking / M&A": Investment bankers, M&A analysts/associates/VPs at banks or advisory firms.
  - "Strategy Consulting": Strategy consultants, management consultants at consulting firms.
  - "Crypto / Web3": Roles explicitly in crypto, blockchain, DeFi, or Web3 companies.
- Generic roles: Sales, Marketing, HR/People, Operations, Executive, Other.

When in doubt between a B2B category and a generic one, prefer the B2B category if the person's title suggests decision-making authority at a financial institution.

Job titles to classify:
{titles}

Respond with ONLY a JSON object mapping each title to its category. Example:
{{"Software Engineer": "Engineering", "Head of Product at Binance": "Broker_Exchange_HeadOfProduct", "CFO": "Executive"}}

JSON response:"""

# Batch size for LLM calls (titles per request)
LLM_BATCH_SIZE = 50

# Module-level cache: {title -> category} persists across searches within the same process
_title_cache: Dict[str, str] = {}


# Progress callback type: (current_batch, total_batches, titles_processed, total_titles)
ProgressCallback = Callable[[int, int, int, int], None]


def cluster_employees_by_role(
    employees: List[Dict[str, Any]],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Cluster employees by role using LLM classification.

    Args:
        employees: List of employee dicts with at least 'title' field.
        progress_callback: Optional callback for progress updates.
            Called with (current_batch, total_batches, titles_processed, total_titles).

    Returns:
        Dict mapping role category to list of employees in that category.
    """
    t_start = time.perf_counter()

    if not employees:
        return {cat: [] for cat in ROLE_CATEGORIES}

    # Extract unique titles
    titles = list(
        {emp.get("title", "").strip() for emp in employees if emp.get("title")}
    )

    if not titles:
        return {"Other": employees}

    t_pre_llm = time.perf_counter()
    logger.info(
        "[TIMING] Pre-LLM setup complete",
        elapsed_ms=round((t_pre_llm - t_start) * 1000, 2),
        unique_titles=len(titles),
        total_employees=len(employees),
    )

    # Get classification from LLM (with batching)
    title_to_category = _classify_titles_with_llm_batched(
        titles, progress_callback=progress_callback
    )

    t_post_llm = time.perf_counter()
    logger.info(
        "[TIMING] LLM classification complete",
        elapsed_ms=round((t_post_llm - t_pre_llm) * 1000, 2),
    )

    # Group employees by category
    clustered: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for emp in employees:
        title = emp.get("title", "").strip()
        category = title_to_category.get(title, "Other")
        clustered[category].append(emp)

    # Ensure all categories exist in output (empty lists for unused categories)
    result = {cat: clustered.get(cat, []) for cat in ROLE_CATEGORIES}

    t_end = time.perf_counter()

    # Log clustering summary
    summary = {cat: len(emps) for cat, emps in result.items() if emps}
    logger.info(
        "[TIMING] Clustering complete",
        post_llm_grouping_ms=round((t_end - t_post_llm) * 1000, 2),
        total_elapsed_ms=round((t_end - t_start) * 1000, 2),
        summary=summary,
        total=len(employees),
    )

    return result


def _classify_titles_with_llm_batched(
    titles: List[str],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, str]:
    """Classify titles using batched LLM calls for better performance.

    Args:
        titles: List of unique job titles.
        progress_callback: Optional callback for progress updates.

    Returns:
        Dict mapping each title to its category.
    """
    if not titles:
        return {}

    # Check cache for already-classified titles
    cached = {t: _title_cache[t] for t in titles if t in _title_cache}
    uncached = [t for t in titles if t not in _title_cache]

    if not uncached:
        logger.info(f"All {len(cached)} titles resolved from cache")
        if progress_callback:
            progress_callback(1, 1, len(cached), len(cached))
        return cached

    if cached:
        logger.info(
            f"{len(cached)} titles from cache, {len(uncached)} need LLM classification"
        )

    # Split uncached titles into batches
    batches = [
        uncached[i : i + LLM_BATCH_SIZE]
        for i in range(0, len(uncached), LLM_BATCH_SIZE)
    ]
    total_batches = len(batches)

    logger.info(
        f"Processing {len(uncached)} titles in {total_batches} batches "
        f"(batch_size={LLM_BATCH_SIZE})"
    )

    all_validated: Dict[str, str] = {}
    titles_processed = 0

    for batch_idx, batch in enumerate(batches, start=1):
        t_batch_start = time.perf_counter()

        batch_result = _classify_single_batch(batch)
        all_validated.update(batch_result)

        titles_processed += len(batch)
        t_batch_end = time.perf_counter()

        logger.info(
            f"[TIMING] Batch {batch_idx}/{total_batches} complete",
            batch_size=len(batch),
            elapsed_ms=round((t_batch_end - t_batch_start) * 1000, 2),
            titles_processed=titles_processed,
            total_titles=len(uncached),
        )

        if progress_callback:
            progress_callback(batch_idx, total_batches, titles_processed, len(uncached))

    # Update cache with all new classifications
    _title_cache.update(all_validated)

    # Merge cached + newly classified
    all_validated.update(cached)
    return all_validated


def _classify_single_batch(titles: List[str]) -> Dict[str, str]:
    """Classify a single batch of titles via LLM.

    Args:
        titles: List of job titles (should be <= LLM_BATCH_SIZE).

    Returns:
        Dict mapping each title to its category.
    """
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


def filter_by_segment(
    clustered: Dict[str, List[Dict[str, Any]]], segment: str
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter clustered role groups by B2C/B2B segment.

    Args:
        clustered: Dict mapping role category to list of employees.
        segment: "b2c", "b2b", or anything else (returns unfiltered).

    Returns:
        Filtered dict with only the roles belonging to the selected segment.
    """
    if segment == "b2c":
        allowed = B2C_ROLES | {
            "Sales",
            "Marketing",
            "HR/People",
            "Operations",
            "Executive",
            "Other",
        }
    elif segment == "b2b":
        allowed = B2B_ROLES
    else:
        return clustered
    return {k: v for k, v in clustered.items() if k in allowed}
