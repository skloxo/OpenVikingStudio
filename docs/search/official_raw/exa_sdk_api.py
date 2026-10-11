from __future__ import annotations

import dataclasses
import json
import os
import re
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from .websets import AsyncWebsetsClient
import httpx
import requests
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat_model import ChatModel
from typing_extensions import TypedDict

from exa_py.utils import (
    ExaOpenAICompletion,
    _convert_schema_input,
    _get_package_version,
    add_message_to_messages,
    format_exa_result,
    maybe_get_query,
    JSONSchemaInput,
)
from .websets import WebsetsClient
from .websets.core.base import ExaJSONEncoder
from .monitors import SearchMonitorsClient, AsyncSearchMonitorsClient
from .research import ResearchClient, AsyncResearchClient


is_beta = os.getenv("IS_BETA") == "True"

# Default max characters for text contents
DEFAULT_MAX_CHARACTERS = 10_000


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str (str): The string in snake_case format.

    Returns:
        str: The string converted to camelCase format.
    """
    # Handle special cases where the field should start with non-alphanumeric characters
    if snake_str == "schema_":
        return "$schema"
    if snake_str == "not_":
        return "not"

    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_camel_case(data: dict, skip_keys: list[str] = []) -> dict:
    """
    Convert keys in a dictionary from snake_case to camelCase recursively.

    Args:
        data (dict): The dictionary with keys in snake_case format.

    Returns:
        dict: The dictionary with keys converted to camelCase format.
    """
    if isinstance(data, dict):
        return {
            snake_to_camel(k): to_camel_case(v, skip_keys)
            if isinstance(v, dict) and k not in skip_keys
            else v
            for k, v in data.items()
            if v is not None
        }
    return data


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Args:
        camel_str (str): The string in camelCase format.

    Returns:
        str: The string converted to snake_case format.
    """
    snake_str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_str).lower()


def to_snake_case(data: dict) -> dict:
    """
    Convert keys in a dictionary from camelCase to snake_case recursively.

    Args:
        data (dict): The dictionary with keys in camelCase format.

    Returns:
        dict: The dictionary with keys converted to snake_case format.
    """
    if isinstance(data, dict):
        return {
            camel_to_snake(k): to_snake_case(v) if isinstance(v, dict) else v
            for k, v in data.items()
        }
    return data


def _parse_entities(entities_data: Optional[List[dict]]) -> Optional[List]:
    """
    Parse entity data from API response into Entity dataclasses.

    Handles field mapping for reserved Python keywords:
    - 'from' -> 'from_date'
    - 'to' -> 'to_date'
    """
    if not entities_data:
        return None

    # Import here to avoid circular imports (Entity types defined later in file)
    from exa_py.api import (
        CompanyEntity,
        PersonEntity,
        EntityCompanyProperties,
        EntityPersonProperties,
        EntityCompanyPropertiesWorkforce,
        EntityCompanyPropertiesHeadquarters,
        EntityCompanyPropertiesFinancials,
        EntityCompanyPropertiesFundingRound,
        EntityCompanyPropertiesWebTraffic,
        EntityDateRange,
        EntityPersonPropertiesCompanyRef,
        EntityPersonPropertiesWorkHistoryEntry,
    )

    def parse_date_range(data: Optional[dict]) -> Optional[EntityDateRange]:
        if not data:
            return None
        return EntityDateRange(
            from_date=data.get("from"),
            to_date=data.get("to"),
        )

    def parse_company_ref(data: Optional[dict]) -> Optional[EntityPersonPropertiesCompanyRef]:
        if not data:
            return None
        return EntityPersonPropertiesCompanyRef(
            id=data.get("id"),
            name=data.get("name"),
        )

    def parse_work_history_entry(data: dict) -> EntityPersonPropertiesWorkHistoryEntry:
        return EntityPersonPropertiesWorkHistoryEntry(
            title=data.get("title"),
            location=data.get("location"),
            dates=parse_date_range(data.get("dates")),
            company=parse_company_ref(data.get("company")),
        )

    def parse_funding_round(data: Optional[dict]) -> Optional[EntityCompanyPropertiesFundingRound]:
        if not data:
            return None
        return EntityCompanyPropertiesFundingRound(
            name=data.get("name"),
            date=data.get("date"),
            amount=data.get("amount"),
        )

    def parse_financials(data: Optional[dict]) -> Optional[EntityCompanyPropertiesFinancials]:
        if not data:
            return None
        return EntityCompanyPropertiesFinancials(
            revenue_annual=data.get("revenueAnnual"),
            funding_total=data.get("fundingTotal"),
            funding_latest_round=parse_funding_round(data.get("fundingLatestRound")),
        )

    def parse_web_traffic(data: Optional[dict]) -> Optional[EntityCompanyPropertiesWebTraffic]:
        if not data:
            return None
        return EntityCompanyPropertiesWebTraffic(
            visits_monthly=data.get("visitsMonthly"),
        )

    def parse_company_properties(data: dict) -> EntityCompanyProperties:
        workforce_data = data.get("workforce")
        headquarters_data = data.get("headquarters")
        return EntityCompanyProperties(
            name=data.get("name"),
            founded_year=data.get("foundedYear"),
            description=data.get("description"),
            workforce=EntityCompanyPropertiesWorkforce(total=workforce_data.get("total")) if workforce_data else None,
            headquarters=EntityCompanyPropertiesHeadquarters(
                address=headquarters_data.get("address"),
                city=headquarters_data.get("city"),
                postal_code=headquarters_data.get("postalCode"),
                country=headquarters_data.get("country"),
            ) if headquarters_data else None,
            financials=parse_financials(data.get("financials")),
            web_traffic=parse_web_traffic(data.get("webTraffic")),
        )

    def parse_person_properties(data: dict) -> EntityPersonProperties:
        work_history = data.get("workHistory")
        return EntityPersonProperties(
            name=data.get("name"),
            location=data.get("location"),
            work_history=[parse_work_history_entry(wh) for wh in work_history] if work_history else None,
        )

    entities = []
    for entity_data in entities_data:
        entity_type = entity_data.get("type")
        if entity_type == "company":
            entities.append(CompanyEntity(
                id=entity_data["id"],
                type="company",
                version=entity_data["version"],
                properties=parse_company_properties(entity_data.get("properties", {})),
            ))
        elif entity_type == "person":
            entities.append(PersonEntity(
                id=entity_data["id"],
                type="person",
                version=entity_data["version"],
                properties=parse_person_properties(entity_data.get("properties", {})),
            ))
    return entities if entities else None


# Category options for search filtering
Category = Literal[
    "company",
    "research paper",
    "news",
    "pdf",
    "personal site",
    "financial report",
    "people",
]
"""Data category to focus on when searching. Each category returns results specialized for that content type."""

# Search type options
SearchType = Literal[
    "auto",
    "fast",
    "deep-lite",
    "deep",
    "deep-reasoning",
    "neural",
    "instant",
]
"""Search type that determines the search algorithm.

'auto' (default) automatically selects the best approach, 'fast' prioritizes
speed, 'deep-lite', 'deep', and 'deep-reasoning' are deep-search variants,
'neural' uses embedding-based semantic search, and 'instant' uses low-latency
neural search.
"""


class DeepTextOutputSchema(TypedDict, total=False):
    """Deep search output schema for plain-text output."""

    type: Literal["text"]
    description: str


class DeepObjectOutputSchema(TypedDict, total=False):
    """Deep search output schema for structured JSON object output."""

    type: Literal["object"]
    properties: Dict[str, Any]
    required: List[str]


DeepOutputSchema = Union[DeepTextOutputSchema, DeepObjectOutputSchema]
"""Search output schema.

- ``{"type": "text", "description": ...}`` returns plain text in ``output.content``.
- ``{"type": "object", ...}`` returns structured JSON in ``output.content``.

For object schemas, the API enforces max nesting depth 2 and max 10 total properties.
"""

SEARCH_OPTIONS_TYPES = {
    "query": [str],  # The query string.
    "num_results": [int],  # Number of results (Default: 10, Max for basic: 10).
    "include_domains": [
        list
    ],  # Domains to search from; exclusive with 'exclude_domains'.
    "exclude_domains": [list],  # Domains to omit; exclusive with 'include_domains'.
    "start_crawl_date": [str],  # Results after this crawl date. ISO 8601 format.
    "end_crawl_date": [str],  # Results before this crawl date. ISO 8601 format.
    "start_published_date": [
        str
    ],  # Results after this publish date; excludes links with no date. ISO 8601 format.
    "end_published_date": [
        str
    ],  # Results before this publish date; excludes links with no date. ISO 8601 format.
    "user_location": [str],  # Two-letter ISO country code of the user (e.g. US).
    "include_text": [
        list
    ],  # Must be present in webpage text. (One string, up to 5 words)
    "exclude_text": [
        list
    ],  # Must not be present in webpage text. (One string, up to 5 words)
    "type": [
        SearchType,
        str,
    ],  # Search type: 'auto', 'fast', 'deep-lite', 'deep', 'deep-reasoning', 'neural', or 'instant' (Default: auto)
    "category": [Category],  # A data category to focus on.
    "flags": [list],  # Experimental flags array for Exa usage.
    "moderation": [bool],  # If true, moderate search results for safety.
    "contents": [dict, bool],  # Options for retrieving page contents
    "additional_queries": [
        list
    ],  # Alternative query formulations for deep search variants (max 5). Only used when type is deep-lite/deep/deep-reasoning.
    "system_prompt": [str],  # Instructions for search planning and final synthesis across all search types.
    "output_schema": [dict],  # Search output schema: {"type":"text"} or {"type":"object", ...}
    "stream": [bool],  # If true, stream back OpenAI-style chat completion chunks.
}

FIND_SIMILAR_OPTIONS_TYPES = {
    "url": [str],
    "num_results": [int],
    "include_domains": [list],
    "exclude_domains": [list],
    "start_crawl_date": [str],
    "end_crawl_date": [str],
    "start_published_date": [str],
    "end_published_date": [str],
    "include_text": [list],
    "exclude_text": [list],
    "exclude_source_domain": [bool],
    "category": [Category],  # A data category to focus on.
    "flags": [list],  # Experimental flags array for Exa usage.
    "contents": [dict, bool],  # Options for retrieving page contents
}

# Livecrawl options
LIVECRAWL_OPTIONS = Literal["always", "fallback", "never", "auto", "preferred"]

CONTENTS_OPTIONS_TYPES = {
    "urls": [list],
    "text": [dict, bool],
    "summary": [dict, bool],
    "highlights": [dict, bool],
    "context": [dict, bool],
    "metadata": [dict, bool],
    "livecrawl_timeout": [int],
    "livecrawl": [LIVECRAWL_OPTIONS],
    "max_age_hours": [int],
    "filter_empty_results": [bool],
    "flags": [list],  # We allow flags to be passed here too
}

CONTENTS_ENDPOINT_OPTIONS_TYPES = {
    "subpages": [int],
    "subpage_target": [str, list],
    "extras": [dict],
    "flags": [list],  # We allow flags to be passed here too
}


def validate_search_options(
    options: Dict[str, Optional[object]], expected: dict
) -> None:
    """Validate an options dict against expected types and constraints.

    Args:
        options (Dict[str, Optional[object]]): The options to validate.
        expected (dict): The expected types for each option.

    Raises:
        ValueError: If an invalid option or option type is provided.
    """
    for key, value in options.items():
        if key not in expected:
            raise ValueError(f"Invalid option: '{key}'")
        if value is None:
            continue
        expected_types = expected[key]
        if not any(is_valid_type(value, t) for t in expected_types):
            raise ValueError(
                f"Invalid value for option '{key}': {value}. Expected one of {expected_types}"
            )


def is_valid_type(value, expected_type):
    if get_origin(expected_type) is Literal:
        return value in get_args(expected_type)
    if isinstance(expected_type, type):
        return isinstance(value, expected_type)
    return False  # For any other case


def parse_cost_dollars(raw: dict) -> Optional[CostDollars]:
    """
    Parse the costDollars JSON into a CostDollars object, or return None if missing/invalid.
    """
    if not raw:
        return None

    total = raw.get("total")
    if total is None:
        # If there's no total, treat as absent
        return None

    # search and contents can be dictionaries or None
    search_part = raw.get("search")
    contents_part = raw.get("contents")

    return CostDollars(total=total, search=search_part, contents=contents_part)


VERBOSITY_OPTIONS = Literal["compact", "standard", "full"]
"""Verbosity levels for content filtering.
- compact: Most concise output, main content only (default)
- standard: Balanced content with more detail
- full: Complete content including all sections
"""

SECTION_TAG = Literal[
    "unspecified", "header", "navigation", "banner", "body", "sidebar", "footer", "metadata"
]
"""Section tags for semantic content filtering."""


class TextContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting text

    Attributes:
        max_characters (int): The maximum number of characters to return. Default: None (no limit).
        include_html_tags (bool): If true, include HTML tags in the returned text. Default false.
        verbosity (VERBOSITY_OPTIONS): Controls verbosity level of returned content.
            "compact" (default): main content only; "standard": balanced; "full": all sections.
            Requires max_age_hours=0 to take effect.
        include_sections (List[SECTION_TAG]): Only include content from these semantic sections.
            Requires max_age_hours=0 to take effect.
        exclude_sections (List[SECTION_TAG]): Exclude content from these semantic sections.
            Requires max_age_hours=0 to take effect.
    """

    max_characters: int
    include_html_tags: bool
    verbosity: VERBOSITY_OPTIONS
    include_sections: List[SECTION_TAG]
    exclude_sections: List[SECTION_TAG]


class JSONSchema(TypedDict, total=False):
    """Represents a JSON Schema definition used for structured summary output.

    .. deprecated:: 1.15.0
        Use Pydantic models or dict[str, Any] directly instead.
        This will be removed in a future version.

    To learn more visit https://json-schema.org/overview/what-is-jsonschema.
    """

    schema_: str  # This will be converted to "$schema" in JSON
    title: str
    description: str
    type: Literal["object", "array", "string", "number", "boolean", "null", "integer"]
    properties: Dict[str, JSONSchema]
    items: Union[JSONSchema, List[JSONSchema]]
    required: List[str]
    enum: List
    additionalProperties: Union[bool, JSONSchema]
    definitions: Dict[str, JSONSchema]
    patternProperties: Dict[str, JSONSchema]
    allOf: List[JSONSchema]
    anyOf: List[JSONSchema]
    oneOf: List[JSONSchema]
    not_: JSONSchema  # This will be converted to "not" in JSON


class SummaryContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting summary

    Attributes:
        query (str): The query string for the summary. Summary will bias towards answering the query.
        schema (Union[BaseModel, dict[str, Any]]): JSON schema for structured output from summary.
            Can be a Pydantic model (automatically converted) or a dict containing JSON Schema.
    """

    query: str
    schema: JSONSchemaInput


class HighlightsContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting highlights.

    Attributes:
        query (str): The query string for highlight generation. Highlights will be biased towards this query.
        max_characters (int): The maximum number of characters to return for highlights. Default: None (server default).
        num_sentences (int): Deprecated. Use max_characters instead. The number of sentences per highlight.
        highlights_per_url (int): Deprecated. Use max_characters instead. The number of highlights to return per URL.
    """

    query: str
    max_characters: int
    num_sentences: int
    highlights_per_url: int


class ContextContentsOptions(TypedDict, total=False):
    """Options for retrieving aggregated context from a set of search results.

    .. deprecated::
        Use ``highlights`` or ``text`` instead. The ``context`` option is deprecated
        and will be removed in a future version.

    Attributes:
        max_characters (int): The maximum number of characters to include in the context string.
    """

    max_characters: int


class ExtrasOptions(TypedDict, total=False):
    """A class representing additional extraction fields (e.g. links, images)"""

    links: int
    image_links: int


class ContentsOptions(TypedDict, total=False):
    """Options for retrieving page contents in search and find_similar methods.

    All fields are optional. If no content options are specified, text with
    max_characters=10000 is returned by default.

    Attributes:
        text (TextContentsOptions | True): Options for text extraction, or True for defaults.
        highlights (HighlightsContentsOptions | True): Options for highlight extraction, or True for defaults.
        summary (SummaryContentsOptions | True): Options for summary generation, or True for defaults.
        context (ContextContentsOptions | True): Deprecated. Use ``highlights`` or ``text`` instead. Will be removed in a future version.
        max_age_hours (int): Maximum age of cached content in hours. If content is older, it will be
            fetched fresh. Special values: 0 = always fetch fresh content,
            -1 = never fetch fresh (use cached content only). Example: 168 = fetch fresh for pages older than 7 days.
        subpages (int): Number of subpages to crawl.
        subpage_target (str | List[str]): Target subpage path(s) to crawl.
        extras (ExtrasOptions): Additional extraction options (links, images).
    """

    text: Union[TextContentsOptions, Literal[True]]
    highlights: Union[HighlightsContentsOptions, Literal[True]]
    summary: Union[SummaryContentsOptions, Literal[True]]
    context: Union[ContextContentsOptions, Literal[True]]
    livecrawl: LIVECRAWL_OPTIONS
    livecrawl_timeout: int
    max_age_hours: int
    subpages: int
    subpage_target: Union[str, List[str]]
    extras: ExtrasOptions


class CostDollarsSearch(TypedDict, total=False):
    """Represents the cost breakdown for search."""

    neural: float
    keyword: float


class CostDollarsContents(TypedDict, total=False):
    """Represents the cost breakdown for contents."""

    text: float
    summary: float


@dataclass
class CostDollars:
    """Represents costDollars field in the API response."""

    total: float
    search: CostDollarsSearch = None
    contents: CostDollarsContents = None


# Entity types for company/people search results
# Only returned when using category="company" or category="people" searches


@dataclass
class EntityCompanyPropertiesWorkforce:
    """Company workforce information."""

    total: Optional[int] = None


@dataclass
class EntityCompanyPropertiesHeadquarters:
    """Company headquarters information."""

    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@dataclass
class EntityCompanyPropertiesFundingRound:
    """Funding round information."""

    name: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[int] = None


@dataclass
class EntityCompanyPropertiesFinancials:
    """Company financial information."""

    revenue_annual: Optional[int] = None
    funding_total: Optional[int] = None
    funding_latest_round: Optional[EntityCompanyPropertiesFundingRound] = None


@dataclass
class EntityCompanyPropertiesWebTraffic:
    """Company web traffic information."""

    visits_monthly: Optional[int] = None


@dataclass
class EntityCompanyProperties:
    """Structured properties for a company entity."""

    name: Optional[str] = None
    founded_year: Optional[int] = None
    description: Optional[str] = None
    workforce: Optional[EntityCompanyPropertiesWorkforce] = None
    headquarters: Optional[EntityCompanyPropertiesHeadquarters] = None
    financials: Optional[EntityCompanyPropertiesFinancials] = None
    web_traffic: Optional[EntityCompanyPropertiesWebTraffic] = None


@dataclass
class EntityDateRange:
    """Date range for work history entries."""

    from_date: Optional[str] = None  # API returns 'from' but it's a reserved keyword
    to_date: Optional[str] = None  # API returns 'to', renamed for consistency


@dataclass
class EntityPersonPropertiesCompanyRef:
    """Reference to a company in work history."""

    id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class EntityPersonPropertiesWorkHistoryEntry:
    """A single work history entry for a person."""

    title: Optional[str] = None
    location: Optional[str] = None
    dates: Optional[EntityDateRange] = None
    company: Optional[EntityPersonPropertiesCompanyRef] = None


@dataclass
class EntityPersonProperties:
    """Structured properties for a person entity."""

    name: Optional[str] = None
    location: Optional[str] = None
    work_history: Optional[List[EntityPersonPropertiesWorkHistoryEntry]] = None


@dataclass
class CompanyEntity:
    """Structured entity data for a company."""

    id: str
    type: Literal["company"]
    version: int
    properties: EntityCompanyProperties


@dataclass
class PersonEntity:
    """Structured entity data for a person."""

    id: str
    type: Literal["person"]
    version: int
    properties: EntityPersonProperties


Entity = Union[CompanyEntity, PersonEntity]


@dataclass
class _Result:
    """A class representing the base fields of a search result.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        score (float, optional): A number from 0 to 1 representing similarity.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): The author of the content (if available).
        image (str, optional): A URL to an image associated with the content (if available).
        favicon (str, optional): A URL to the favicon (if available).
        subpages (List[_Result], optional): Subpages of main page
        extras (Dict, optional): Additional metadata; e.g. links, images.
        entities (List[Entity], optional): Structured entity data for company or person searches.
        crawl_date (str, optional): The date the page was last crawled (if available).
    """

    url: str
    id: str
    title: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    image: Optional[str] = None
    favicon: Optional[str] = None
    subpages: Optional[List[_Result]] = None
    extras: Optional[Dict] = None
    entities: Optional[List[Entity]] = None
    crawl_date: Optional[str] = None

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        entities=None,
        crawl_date=None,
    ):
        self.url = url
        self.id = id
        self.title = title
        self.score = score
        self.published_date = published_date
        self.author = author
        self.image = image
        self.favicon = favicon
        self.subpages = subpages
        self.extras = extras
        self.entities = entities
        self.crawl_date = crawl_date

    def __str__(self):
        result = (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"ID: {self.id}\n"
            f"Score: {self.score}\n"
            f"Published Date: {self.published_date}\n"
            f"Author: {self.author}\n"
            f"Image: {self.image}\n"
            f"Favicon: {self.favicon}\n"
            f"Extras: {self.extras}\n"
            f"Subpages: {self.subpages}\n"
            f"Crawl Date: {self.crawl_date}\n"
        )
        if self.entities:
            entities_str = "\n".join(
                f"  - [{e.type}] {e.properties.name or 'Unknown'}"
                for e in self.entities
            )
            result += f"Entities:\n{entities_str}\n"
        return result


@dataclass
class Result(_Result):
    """
    A class representing a search result with optional text, summary, and highlights.

    Attributes:
        text (str, optional): The text content of the page.
        summary (str, optional): A summary of the page content.
        highlights (List[str], optional): Relevant sentences from the page.
        highlight_scores (List[float], optional): Scores for each highlight.
    """

    text: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None
    highlight_scores: Optional[List[float]] = None

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        entities=None,
        crawl_date=None,
        text=None,
        summary=None,
        highlights=None,
        highlight_scores=None,
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
            entities,
            crawl_date,
        )
        self.text = text
        self.summary = summary
        self.highlights = highlights
        self.highlight_scores = highlight_scores

    def __str__(self):
        base_str = super().__str__()
        result = base_str + f"Text: {self.text}\nSummary: {self.summary}\n"
        if self.highlights:
            result += f"Highlights: {self.highlights}\n"
        if self.highlight_scores:
            result += f"Highlight Scores: {self.highlight_scores}\n"
        return result


@dataclass
class ResultWithText(_Result):
    """
    A class representing a search result with text present.

    Attributes:
        text (str): The text of the search result page.
    """

    text: str = dataclasses.field(default_factory=str)

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        entities=None,
        crawl_date=None,
        text="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
            entities,
            crawl_date,
        )
        self.text = text

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n"


@dataclass
class ResultWithSummary(_Result):
    """
    A class representing a search result with summary present.

    Attributes:
        summary (str)
    """

    summary: str = dataclasses.field(default_factory=str)

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        entities=None,
        crawl_date=None,
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
            entities,
            crawl_date,
        )
        self.summary = summary

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Summary: {self.summary}\n"


@dataclass
class ResultWithTextAndSummary(_Result):
    """
    A class representing a search result with text and summary present.

    Attributes:
        text (str)
        summary (str)
    """

    text: str = dataclasses.field(default_factory=str)
    summary: str = dataclasses.field(default_factory=str)

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        entities=None,
        crawl_date=None,
        text="",
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
            entities,
            crawl_date,
        )
        self.text = text
        self.summary = summary

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n" + f"Summary: {self.summary}\n"


@dataclass
class AnswerResult:
    """A class representing a result for an answer.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): If available, the author of the content.
        text (str, optional): The full page text from each search result.
    """

    id: str
    url: str
    title: Optional[str] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None

    def __init__(
        self, id, url, title=None, published_date=None, author=None, text=None
    ):
        self.id = id
        self.url = url
        self.title = title
        self.published_date = published_date
        self.author = author
        self.text = text

    def __str__(self):
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"ID: {self.id}\n"
            f"Published Date: {self.published_date}\n"
            f"Author: {self.author}\n"
            f"Text: {self.text}\n\n"
        )


@dataclass
class StreamChunk:
    """A class representing a single chunk of streaming data.

    Attributes:
        content (Optional[str]): The partial text content of the streamed response.
        citations (Optional[List[AnswerResult]]): List of citations if provided in this chunk.
    """

    content: Optional[str] = None
    citations: Optional[List[AnswerResult]] = None

    def has_data(self) -> bool:
        """Check if this chunk contains any data."""
        return self.content is not None or self.citations is not None

    def __str__(self) -> str:
        """Format the chunk data as a string."""
        output = ""
        if self.content:
            output += self.content
        if self.citations:
            output += "\nCitations:"
            for source in self.citations:
                output += f"\n{source}"
        return output


@dataclass
class AnswerResponse:
    """A class representing the response for an answer operation.

    Attributes:
        answer (str): The generated answer.
        citations (List[AnswerResult]): A list of citations used to generate the answer.
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
    """

    answer: Union[str, dict[str, Any]]
    citations: List[AnswerResult]
    cost_dollars: Optional[CostDollars] = None

    def __str__(self):
        output = f"Answer: {self.answer}\n\nCitations:"
        for source in self.citations:
            output += f"\nTitle: {source.title}"
            output += f"\nID: {source.id}"
            output += f"\nURL: {source.url}"
            output += f"\nPublished Date: {source.published_date}"
            output += f"\nAuthor: {source.author}"
            output += f"\nText: {source.text}"
            output += "\n"
        return output


class StreamAnswerResponse:
    """A class representing a streaming answer response."""

    def __init__(self, raw_response: requests.Response):
        self._raw_response = raw_response
        self._ensure_ok_status()

    def _ensure_ok_status(self):
        if self._raw_response.status_code != 200:
            raise ValueError(
                f"Request failed with status code {self._raw_response.status_code}: {self._raw_response.text}"
            )

    def __iter__(self) -> Iterator[StreamChunk]:
        for line in self._raw_response.iter_lines():
            if not line:
                continue
            decoded_line = line.decode("utf-8").removeprefix("data: ")
            try:
                chunk = json.loads(decoded_line)
            except json.JSONDecodeError:
                continue

            content = None
            citations = None

            if "choices" in chunk and chunk["ch