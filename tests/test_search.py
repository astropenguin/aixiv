# dependencies
from aixiv.search import search


# constants
CATEGORIES = ("astro-ph.GA",)
KEYWORDS = ("galaxy",)
START_DATE = "2021-01-01 in UTC"
END_DATE = "2021-01-02 in UTC"
EXPECTED_URLS = [
    "http://arxiv.org/abs/2101.00188v2",
    "http://arxiv.org/abs/2101.00158v1",
    "http://arxiv.org/abs/2101.00253v3",
    "http://arxiv.org/abs/2101.00283v1",
]


# test functions
def test_search() -> None:
    articles = search(
        categories=CATEGORIES,
        keywords=KEYWORDS,
        start_date=START_DATE,
        end_date=END_DATE,
    )
    urls = [article.url for article in articles]
    assert urls == EXPECTED_URLS
