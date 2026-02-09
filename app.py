from flask import Flask, render_template, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)


@app.context_processor
def utility_processor():
    def static_url(path: str) -> str:
        return app.url_for('static', filename=path)

    return {'static_url': static_url}

def get_latest_articles(limit=10):
    """
    Fetch the latest articles from the 'articles' table,
    sorted by date_added (descending), limited to 'limit' results.
    """
    db_path = os.path.join(os.path.dirname(__file__), 'articles.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Ensure your table is named 'articles' as in your scripts
    cursor.execute('''
        SELECT 
            id, source, url, title, author, article_text,
            core_thesis, detailed_abstract, supporting_data_quotes, date_added
        FROM articles
        ORDER BY date_added DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()

    articles = []
    for row in rows:
        articles.append({
            "id": row[0],
            "source": row[1],
            "url": row[2],
            "title": row[3],
            "author": row[4],
            "article_text": row[5],
            "core_thesis": row[6],
            "detailed_abstract": row[7],
            "supporting_data_quotes": row[8],
            "date_added": row[9],
        })
    articles.reverse()  # Reverse the order to show latest
    return articles

@app.route('/')
def home():
    """
    Main route: Fetch and display the latest articles in a card-based layout.
    Articles are sorted latest-first by date_added DESC.
    """
    articles = get_latest_articles(limit=20)
    return render_template('index.html', articles=articles)


@app.route('/api/articles')
def api_articles():
    """Return latest articles in JSON format."""
    articles = get_latest_articles(limit=20)
    return jsonify(articles)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
