__all__ = ["Article", "amap"]


# standard library
from asyncio import TimeoutError, gather, run, sleep, wait_for
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field, replace
from logging import getLogger
from reprlib import Repr
from typing import Optional, TypeVar, Union


# dependencies
from arxiv import Result
from limits import parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter
from typing_extensions import Self
from .defaults import LIMIT, TIMEOUT


# type hints
TArticle = TypeVar("TArticle", bound="Article")
Finally = Union[TArticle, Awaitable[TArticle]]


# constants
INTERVAL = 0.1
LOGGER = getLogger(__name__)
UNLIMITED = parse("1000/second")


@dataclass(frozen=True)
class Article:
    """Article information.

    Args:
        title: Title of the article.
        authors: Authors of the article.
        summary: Summary of the article.
        url: URL of the article.
        origin: Original article (if any).

    """

    title: str
    """Title of the article."""

    authors: list[str]
    """Authors of the article."""

    summary: str
    """Summary of the article."""

    url: str
    """URL of the article."""

    origin: Optional[Self] = field(default=None, repr=False)
    """Original article (if any)."""

    @classmethod
    def from_arxiv(cls, result: Result, /) -> Self:
        """Create an article from an arXiv query result."""

        return cls(
            title=result.title,
            authors=[author.name for author in result.authors],
            summary=result.summary,
            url=result.entry_id,
        )

    def __format__(self, format_spec: str, /) -> str:
        """Support shortened representation of the article."""
        if not format_spec:
            return super().__format__(format_spec)
        else:
            repr = Repr()
            repr.maxother = int(format_spec)
            return repr.repr(self)


def amap(
    func: Callable[[TArticle], Finally[TArticle]],
    articles: Iterable[TArticle],
    /,
    *,
    limit: Optional[str] = LIMIT,
    timeout: float = TIMEOUT,
) -> list[TArticle]:
    """Article-to-article map function.

    Args:
        func: Function or coroutine function for mapping.
        articles: Articles to be mapped.
        limit: Rate limit for the function executions.
            If it is ``None``, (almost) no rate limit is set.
        timeout: Timeout per article in seconds.
            Only used when ``func`` is a coroutine function.

    Returns:
        List of mapped articles by ``func`` with each
        original article stored in the ``origin`` attribute.
        If timeout occurs, the original article is returned.

    """

    async def afunc(article: TArticle, /) -> TArticle:
        if isinstance(result := func(article), Awaitable):
            return replace(await result, origin=article)
        else:
            return replace(result, origin=article)

    async def main() -> list[TArticle]:
        storage = MemoryStorage()
        rate_limiter = MovingWindowRateLimiter(storage)

        if limit is None:
            rate_limit = UNLIMITED
        else:
            rate_limit = parse(limit)

        async def runner(article: TArticle, /) -> TArticle:
            while not await rate_limiter.hit(rate_limit):
                await sleep(INTERVAL)

            try:
                LOGGER.debug(f"Start processing {article:100}.")
                return await wait_for(afunc(article), timeout)
            except TimeoutError:
                LOGGER.warning(
                    f"Timeout in processing {article:100}."
                    "The original article was returned instead."
                )
                return article
            finally:
                LOGGER.debug(f"Finish processing {article:100}.")

        return list(await gather(*map(runner, articles)))

    return run(main())
