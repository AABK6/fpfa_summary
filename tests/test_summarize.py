import unittest
from unittest.mock import patch, MagicMock
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

if __name__ == '__main__':
    unittest.main()
