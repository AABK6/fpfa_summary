import unittest
from unittest.mock import patch, MagicMock
import sys
import summarize_fa_hardened
import summarize_fp

class TestSummarizeFAHardened(unittest.TestCase):
    def test_extract_fa_article_basic(self):
        """Test extraction logic from HTML for Foreign Affairs (Hardened)."""
        html = """
        <html>
            <body>
                <h1 class="topper__title">Test Title</h1>
                <h3 class="topper__byline">Test Author</h3>
                <meta property="article:published_time" content="2024-01-01">
                <article>
                    <p>Paragraph 1</p>
                    <p>Paragraph 2</p>
                </article>
            </body>
        </html>
        """
        with patch('summarize_fa_hardened.fetch_html', return_value=html):
            result = summarize_fa_hardened.extract_foreign_affairs_article("http://test.com")
            self.assertEqual(result['title'], "Test Title")
            self.assertEqual(result['author'], "Test Author")
            self.assertIn("Paragraph 1", result['text'])
            self.assertEqual(result['publication_date'], "2024-01-01")

    def test_extract_latest_article_urls(self):
        """Test extracting latest URLs for Foreign Affairs (Hardened)."""
        html = """
        <html>
            <body>
                <div class="card--large">
                    <h3 class="body-m"><a href="/article/1">Article 1</a></h3>
                </div>
                <div class="card--large">
                    <h4 class="body-s"><a href="/article/2">Article 2</a></h4>
                </div>
                 <div class="card--large">
                    <h3 class="body-m"><a href="/podcasts/skip">Podcast</a></h3>
                </div>
            </body>
        </html>
        """
        with patch('summarize_fa_hardened.fetch_html', return_value=html):
            urls = summarize_fa_hardened.extract_latest_article_urls(num_links=5)
            self.assertEqual(len(urls), 2)
            self.assertIn("https://www.foreignaffairs.com/article/1", urls)
            self.assertIn("https://www.foreignaffairs.com/article/2", urls)

class TestSummarizeFP(unittest.TestCase):
    @patch('requests.get')
    def test_scrape_fp_article_basic(self, mock_get):
        """Test extraction logic for Foreign Policy."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div class="hed-heading"><h1 class="hed">FP Title</h1></div>
                <meta name="author" content="FP Author">
                <meta property="article:published_time" content="2024-02-03">
                <div class="content-ungated">
                    <p>FP Paragraph</p>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        result = summarize_fp.scrape_foreignpolicy_article("http://test-fp.com")
        self.assertEqual(result['title'], "FP Title")
        self.assertEqual(result['author'], "FP Author")
        self.assertIn("FP Paragraph", result['text'])
        self.assertEqual(result['publication_date'], "2024-02-03")



    @patch('requests.get')
    def test_scrape_fp_article_fallback_collects_fuller_body(self, mock_get):
        """Falls back to generic article container if ungated/gated wrappers are absent."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div class="hed-heading"><h1 class="hed">Fallback Title</h1></div>
                <meta name="author" content="Fallback Author">
                <article>
                    <p>Paragraph one has substantial policy analysis content.</p>
                    <p>Paragraph two extends the argument with historical context.</p>
                    <p>Read more from Foreign Policy newsletters</p>
                </article>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = summarize_fp.scrape_foreignpolicy_article("http://test-fp-fallback.com")
        self.assertEqual(result['title'], "Fallback Title")
        self.assertEqual(result['author'], "Fallback Author")
        self.assertIn("substantial policy analysis", result['text'])
        self.assertIn("historical context", result['text'])
        self.assertNotIn("Read more", result['text'])

    @patch('requests.get')
    def test_scrape_fp_article_list(self, mock_get):
        """Test extracting article list for Foreign Policy."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div class="blog-list-layout">
                    <figure class="figure-image">
                        <a href="https://foreignpolicy.com/article/1"></a>
                    </figure>
                </div>
                <div class="blog-list-layout">
                    <figure class="figure-image">
                        <a href="https://foreignpolicy.com/article/2"></a>
                    </figure>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        urls = summarize_fp.scrape_foreignpolicy_article_list(num_links=5)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://foreignpolicy.com/article/1", urls)
        self.assertIn("https://foreignpolicy.com/article/2", urls)

    @patch('requests.get')
    def test_scrape_fp_article_prefers_json_ld_date_over_stray_time_tags(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <script type="application/ld+json">
                    {"@context":"https://schema.org","@type":"NewsArticle","datePublished":"2026-02-19T20:03:47Z"}
                </script>
            </head>
            <body>
                <div class="hed-heading"><h1 class="hed">FP Title</h1></div>
                <meta name="author" content="FP Author">
                <time datetime="2099-03-09" class="date-time"></time>
                <time datetime="2099-04-13" class="date-time"></time>
                <div class="content-ungated">
                    <p>FP Paragraph</p>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        result = summarize_fp.scrape_foreignpolicy_article(
            "https://foreignpolicy.com/2026/02/19/test-article/"
        )
        self.assertEqual(result["publication_date"], "2026-02-19")

    @patch("summarize_fp.scrape_foreignpolicy_article")
    def test_collect_eligible_articles_stops_after_requested_count(self, mock_scrape_article):
        mock_scrape_article.side_effect = [
            {
                "title": "Eligible One",
                "author": "Author",
                "text": "A" * 1200,
                "publication_date": "2026-03-27",
                "content_warning": None,
            },
            {
                "title": "Truncated",
                "author": "Author",
                "text": "short",
                "publication_date": "2026-03-27",
                "content_warning": "possibly_truncated",
            },
            {
                "title": "Eligible Two",
                "author": "Author",
                "text": "B" * 1200,
                "publication_date": "2026-03-27",
                "content_warning": None,
            },
            {
                "title": "Unused",
                "author": "Author",
                "text": "C" * 1200,
                "publication_date": "2026-03-27",
                "content_warning": None,
            },
        ]

        articles, truncated_skips, scrape_failures = summarize_fp.collect_eligible_articles(
            ["url-1", "url-2", "url-3", "url-4"],
            desired_count=2,
        )

        self.assertEqual(len(articles), 2)
        self.assertEqual([article["url"] for article in articles], ["url-1", "url-3"])
        self.assertEqual(truncated_skips, 1)
        self.assertEqual(scrape_failures, 0)
        self.assertEqual(mock_scrape_article.call_count, 3)

    @patch("summarize_fp.resolve_articles_db_path", return_value=":memory:")
    @patch("summarize_fp.init_db")
    @patch("summarize_fp.scrape_foreignpolicy_article")
    @patch("summarize_fp.scrape_foreignpolicy_article_list")
    def test_main_treats_all_truncated_candidates_as_noop(
        self,
        mock_scrape_article_list,
        mock_scrape_article,
        mock_init_db,
        _mock_resolve_path,
    ):
        mock_scrape_article_list.return_value = [f"url-{index}" for index in range(10)]
        mock_scrape_article.side_effect = [
            {
                "title": f"Title {index}",
                "author": "Author",
                "text": "short",
                "publication_date": "2026-03-27",
                "content_warning": "possibly_truncated",
            }
            for index in range(10)
        ]

        mock_repo = MagicMock()
        mock_init_db.return_value = mock_repo

        with patch.object(sys, "argv", ["summarize_fp.py", "2"]):
            with patch("builtins.print") as mock_print:
                summarize_fp.main()

        mock_scrape_article_list.assert_called_once_with(10)
        mock_repo.close.assert_called_once()
        printed_lines = [
            call.args[0]
            for call in mock_print.call_args_list
            if call.args and isinstance(call.args[0], str)
        ]
        self.assertTrue(
            any("Treating this run as a no-op." in line for line in printed_lines),
            printed_lines,
        )

if __name__ == '__main__':
    unittest.main()
