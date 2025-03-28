from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import validators
import requests
from requests.exceptions import RequestException
from datetime import datetime
from bs4 import BeautifulSoup

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


def get_db():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = True
    return conn


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['GET'])
def urls():
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('''
            SELECT u.id, u.name, MAX(uc.created_at), MAX(uc.status_code)
            FROM urls u
            LEFT JOIN url_checks uc ON u.id = uc.url_id
            GROUP BY u.id, u.name
            ORDER BY u.id DESC
        ''')
        urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url', '').strip()

    if not url or len(url) > 255 or not validators.url(url):
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute('SELECT id FROM urls '
                        'WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))', (url,))
            if existing := cur.fetchone():
                flash('Страница уже существует', 'info')
                return redirect(url_for('url_detail', id=existing[0]))

            cur.execute('INSERT INTO urls (name)'
                        ' VALUES (%s) RETURNING id', (url,))
            new_id = cur.fetchone()[0]
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('url_detail', id=new_id))

    except Exception as e:
        flash(f'Ошибка базы данных: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/urls/<int:id>')
def url_detail(id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('SELECT * FROM urls WHERE id = %s', (id,))
        url = cur.fetchone()

        cur.execute('''
            SELECT * FROM url_checks
            WHERE url_id = %s
            ORDER BY id DESC
        ''', (id,))
        checks = cur.fetchall()

    return render_template('url_detail.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def add_check(id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('SELECT name FROM urls WHERE id = %s', (id,))
        url = cur.fetchone()

        if not url:
            flash('URL не найден!', 'danger')
            return redirect(url_for('urls'))

        url = url[0]

        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            h1 = soup.find('h1')
            title = soup.find('title')
            description = soup.find('meta', attrs={'name': 'description'})

            h1_content = h1.text if h1 else ''
            title_content = title.text if title else ''
            description_content = description['content'] if description else ''

            status_code = response.status_code

        except RequestException:
            flash('Произошла ошибка при проверке', 'danger')
            return redirect(url_for('url_detail', id=id))

        cur.execute(
            '''
            INSERT INTO url_checks (url_id, status_code,
            h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (id, status_code, h1_content, title_content,
             description_content, datetime.now())
        )
        conn.commit()

    flash('Страница успешно проверена', 'success')
    return redirect(url_for('url_detail', id=id))


if __name__ == '__main__':
    app.run(debug=True)
