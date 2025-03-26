from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import validators

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


def get_db():
    """Возвращает соединение с базой данных с автоматическим commit при выходе"""
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
            SELECT u.id, u.name, u.created_at, MAX(uc.created_at) as last_check
            FROM urls u
            LEFT JOIN url_checks uc ON u.id = uc.url_id
            GROUP BY u.id, u.name, u.created_at
            ORDER BY u.id DESC
        ''')
        urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url', '').strip()

    # Базовая валидация URL
    if not url or len(url) > 255 or not validators.url(url):
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute('SELECT id FROM urls WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))', (url,))
            if existing := cur.fetchone():
                flash('Страница уже существует', 'info')
                return redirect(url_for('url_detail', id=existing[0]))

            # Добавляем URL
            cur.execute('INSERT INTO urls (name) VALUES (%s) RETURNING id', (url,))
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
def check_url(id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO url_checks (url_id) VALUES (%s)', (id,))
        conn.commit()
    flash('Страница успешно проверена', 'success')
    return redirect(url_for('url_detail', id=id))


if __name__ == '__main__':
    app.run(debug=True)
