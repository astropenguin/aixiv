__all__ = ["Article", "search"]


# standard library
from collections.abc import Sequence
from dataclasses import dataclass, field
from logging import getLogger
from re import compile
from textwrap import shorten
from typing import Optional


# dependencies
from arxiv import Client, Result, Search
from dateparser import parse
from pylatexenc.latex2text import LatexNodes2Text
from typing_extensions import Self
from .defaults import (
    KEYWORDS,
    CATEGORIES,
    START_DATE,
    END_DATE,
    DETEX,
    MAXIMUM,
)


# constants
ARXIV_DATE_FORMAT = "%Y%m%d%H%M%S"
DETEXER = LatexNodes2Text(keep_comments=True)
LOGGER = getLogger(__name__)
SEP_PATTERN = compile(r"\n+\s*|\n*\s+")
SEP_REPL = " "


@dataclass
class Article:
    """Article information."""

    title: str
    """Title of the article."""

    authors: list[str]
    """Authors of the article."""

    summary: str
    """Summary of the article."""

    url: str
    """URL of the article."""

    origin: Optional[Self] = field(default=None, repr=False)
    """Original article (if it exists)."""

    @classmethod
    def from_arxiv(cls, result: Result, /) -> Self:
        """Create an article from an arXiv query result."""
        return cls(
            title=result.title,
            authors=[author.name for author in result.authors],
            summary=result.summary,
            url=result.entry_id,
        )

    def __post_init__(self) -> None:
        """Convert all separators to a single whitespace."""
        self.title = SEP_PATTERN.sub(SEP_REPL, self.title)
        self.summary = SEP_PATTERN.sub(SEP_REPL, self.summary)


def format_date(date_like: str, /) -> str:
    """Parse and format a date-like string."""
    if (dt := parse(date_like)) is not None:
        return dt.strftime(ARXIV_DATE_FORMAT)

    raise ValueError(f"Could not parse {date_like!r}.")


def format_text(text_like: str, /) -> str:
    """Parse and format a text-like string (detex)."""
    try:
        return DETEXER.latex_to_text(text_like)
    except Exception:
        LOGGER.warning(
            f"Failed to format {shorten(text_like, 100)!r}. "
            "The original string was returned instead."
        )
        return text_like


def search(
    categories: Sequence[str] = CATEGORIES,
    keywords: Sequence[str] = KEYWORDS,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
    *,
    detex: bool = DETEX,
    maximum: int = MAXIMUM,
) -> list[Article]:
    """Search for articles in arXiv.

    Args:
        categories: arXiv categories.
        keywords: Keywords of the search.
        start_date: Start date (and time) of the search.
        end_date: End date (and time) of the search.
        detex: Whether to convert LaTeX commands to Unicode.
        maximum: Maximum number of articles to search.

    Returns:
        Articles found with given conditions.

    """
    start_date = format_date(start_date)
    end_date = format_date(end_date)

    query = f"submittedDate:[{start_date} TO {end_date}]"

    if categories:
        sub = " OR ".join(f"cat:{cat}" for cat in categories)
        query += f" AND ({sub})"

    if keywords:
        sub = " OR ".join(f'abs:"{kwd}"' for kwd in keywords)
        query += f" AND ({sub})"

    client = Client()
    search = Search(query, max_results=maximum)
    articles = list(map(Article.from_arxiv, client.results(search)))
    LOGGER.debug(f"Query for search: {query!r}")
    LOGGER.debug(f"Number of articles found: {len(articles)}")

    if detex:
        for article in articles:
            article.title = format_text(article.title)
            article.summary = format_text(article.summary)

    return articles
