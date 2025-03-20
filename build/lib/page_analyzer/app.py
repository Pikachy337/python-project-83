from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import os
import validators
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/urls', methods=['GET'])
def urls():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls ORDER BY created_at DESC;')
    urls = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('urls.html', urls=urls)

@app.route('/urls/<int:id>')
def url_detail(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM urls WHERE id = %s;', (id,))
    url = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('url_detail.html', url=url)

@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url')
    if not url or not validators.url(url) or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM urls WHERE name = %s;', (url,))
    existing_url = cur.fetchone()

    if existing_url:
        flash('URL уже существует', 'info')
        cur.close()
        conn.close()
        return redirect(url_for('url_detail', id=existing_url[0]))

    cur.execute('INSERT INTO urls (name) VALUES (%s) RETURNING id;', (url,))
    new_url_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('url_detail', id=new_url_id))


if __name__ == '__main__':
    app.run(debug=True)
