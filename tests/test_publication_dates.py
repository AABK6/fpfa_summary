from datetime import date

from bs4 import BeautifulSoup

from services.publication_dates import (
    coerce_publication_date,
    extract_publication_date_from_soup,
    normalize_publication_date,
)


def test_normalize_publication_date_handles_iso_datetime():
    assert (
        normalize_publication_date("2026-02-11T00:00:00-05:00", now=date(2026, 3, 6))
        == "2026-02-11"
    )


def test_normalize_publication_date_rejects_future_dates():
    assert normalize_publication_date("2026-03-12", now=date(2026, 3, 6)) is None


def test_coerce_publication_date_falls_back_to_url_date():
    assert (
        coerce_publication_date(
            "2026-04-13",
            url="https://foreignpolicy.com/2026/02/19/example-article/",
            now=date(2026, 3, 6),
        )
        == "2026-02-19"
    )


def test_extract_publication_date_prefers_json_ld_to_stray_future_time_tags():
    soup = BeautifulSoup(
        """
        <html>
            <head>
                <script type="application/ld+json">
                    {"@context":"https://schema.org","@type":"NewsArticle","datePublished":"2026-02-19T20:03:47Z"}
                </script>
            </head>
            <body>
                <time datetime="2099-03-09" class="date-time"></time>
                <time datetime="2099-04-13" class="date-time"></time>
                <time datetime="2026-02-19" class="date-time"></time>
            </body>
        </html>
        """,
        "html.parser",
    )

    assert (
        extract_publication_date_from_soup(
            soup,
            url="https://foreignpolicy.com/2026/02/19/example-article/",
            now=date(2026, 3, 6),
        )
        == "2026-02-19"
    )
