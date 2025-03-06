from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def get_latest_articles(limit=10, specific_article_id=None):
    """
    Fetch the latest articles from the 'articles' table,
    sorted by date_added (descending), limited to 'limit' results.
    If specific_article_id is provided, ensure that article is included in the results.
    """
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    
    articles = []
    
    # If a specific article ID is requested, fetch it first
    if specific_article_id is not None:
        cursor.execute('''
            SELECT 
                id, source, url, title, author, article_text,
                core_thesis, detailed_abstract, supporting_data_quotes, date_added
            FROM articles
            WHERE id = ?
        ''', (specific_article_id,))
        row = cursor.fetchone()
        if row:
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
    
    # Fetch the latest articles
    # If we already have the specific article, exclude it from the query to avoid duplicates
    if specific_article_id is not None and articles:
        cursor.execute('''
            SELECT 
                id, source, url, title, author, article_text,
                core_thesis, detailed_abstract, supporting_data_quotes, date_added
            FROM articles
            WHERE id != ?
            ORDER BY date_added DESC
            LIMIT ?
        ''', (specific_article_id, limit))
    else:
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
    
    # Add the latest articles to our results
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
    
    # Reverse the order to show latest first (but keep specific article at the beginning if present)
    if not specific_article_id:
        articles.reverse()
    
    return articles

@app.route('/')
def home():
    """
    Main route: Fetch and display the latest articles in a card-based layout.
    Articles are sorted latest-first by date_added DESC.
    If article_id is specified in URL parameters, ensure that article is included.
    """
    highlight_id = request.args.get('article_id', type=int)
    state = request.args.get('state', type=int)
    articles = get_latest_articles(limit=20, specific_article_id=highlight_id)
    return render_template('index.html', articles=articles, highlight_id=highlight_id, state=state)

if __name__ == "__main__":
    app.run(debug=True)
