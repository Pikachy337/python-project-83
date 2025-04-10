from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os
import validators
import requests
from requests.exceptions import RequestException
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


def validate_and_normalize_url(url):
    """Validates and normalizes a URL."""
    if not url:
        raise ValueError("URL обязателен")

    if len(url) > 255:
        raise ValueError("URL превышает 255 символов")

    if not validators.url(url):
        raise ValueError("Некорректный URL")

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_seo_data(html):
    """Extracts H1, Title, and Description from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    h1 = (soup.h1.get_text().strip()[:255] if soup.h1 else '')
    title = (soup.title.get_text().strip()[:255] if soup.title else '')
    description = (
        soup.find('meta',
                  attrs={'name': 'description'})['content'].strip()[:255]
        if soup.find('meta', attrs={'name': 'description'}) else ''
    )

    return {'h1': h1, 'title': title, 'description': description}


def get_db():
    """Establishes and returns a connection to the PostgreSQL database."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.autocommit = True
    return conn


@app.route("/")
def index():
    """Renders the homepage with a form to submit a new URL."""
    return render_template("index.html")


@app.route("/urls", methods=["GET"])
def urls():
    """
    Displays a list of all URLs in the database with their latest check status.
    Sorted by ID in descending order (newest first).
    """
    with get_db() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.name, MAX(uc.created_at), MAX(uc.status_code)
            FROM urls u
            LEFT JOIN url_checks uc ON u.id = uc.url_id
            GROUP BY u.id, u.name
            ORDER BY u.id DESC
        """
        )
        urls = cur.fetchall()
    return render_template("urls.html", urls=urls)


@app.route("/urls", methods=["POST"])
def add_url():
    """
    Handles URL submission:
    - Validates the URL format and length
    - Extracts the domain (netloc)
    - Checks if URL already exists in DB
    - Adds new URL if unique
    - Redirects to the URL's detail page
    """
    url = request.form.get("url", "").strip()

    try:
        normalized_url = validate_and_normalize_url(url)
    except ValueError as e:
        flash(str(e), "danger")
        return render_template("index.html", error_message=str(e)), 422

    try:
        domain = urlparse(normalized_url).netloc.lower()
    except Exception:
        flash("Ошибка обработки URL", "danger")
        return redirect(url_for("index"))

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM urls WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
                (domain,),
            )
            existing = cur.fetchone()
    except Exception:
        flash("Ошибка проверки URL в базе", "danger")
        return redirect(url_for("index"))

    if existing:
        flash("Страница уже существует", "info")
        return redirect(url_for("url_detail", id=existing[0]))

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO urls (name) VALUES (%s) RETURNING id",
                (domain,)
            )
            new_id = cur.fetchone()[0]
    except Exception as e:
        flash("Ошибка добавления URL", "danger")
        return redirect(url_for("index"))

    flash("Страница успешно добавлена", "success")
    return redirect(url_for("url_detail", id=new_id))


@app.route("/urls/<int:id>")
def url_detail(id):
    """
    Displays detailed information about a specific URL:
    - URL metadata
    - All historical checks (status codes, timestamps)
    """
    with get_db() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM urls WHERE id = %s", (id,))
        url = cur.fetchone()

        cur.execute(
            """
            SELECT * FROM url_checks
            WHERE url_id = %s
            ORDER BY id DESC
        """,
            (id,),
        )
        checks = cur.fetchall()

    return render_template("url_detail.html", url=url, checks=checks)


@app.route("/urls/<int:id>/checks", methods=["POST"])
def add_check(id):
    """
    Performs a website check:
    - Fetches the URL content
    - Extracts h1, title, and meta description
    - Records HTTP status code and timestamp
    - Stores results in database
    """
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute("SELECT name FROM urls WHERE id = %s", (id,))
            url = cur.fetchone()
    except Exception:
        flash("Ошибка доступа к базе данных", "danger")
        return redirect(url_for("urls"))

    if not url:
        flash("URL не найден!", "danger")
        return redirect(url_for("urls"))

    url = url[0]
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = "http://" + url
    except Exception:
        flash("Ошибка обработки URL", "danger")
        return redirect(url_for("url_detail", id=id))

    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        response.raise_for_status()
    except RequestException as e:
        flash(f"Ошибка при запросе: {str(e)}", "danger")
        return redirect(url_for("url_detail", id=id))

    try:
        seo_data = parse_seo_data(response.text)
    except Exception:
        flash("Ошибка анализа страницы", "danger")
        seo_data = {'h1': '', 'title': '', 'description': ''}

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO url_checks
                (url_id, status_code, h1, title, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    id,
                    response.status_code,
                    seo_data['h1'],
                    seo_data['title'],
                    seo_data['description'],
                    datetime.now(),
                ),
            )
            conn.commit()
    except Exception:
        flash("Ошибка сохранения проверки", "danger")
        return redirect(url_for("url_detail", id=id))

    flash("Страница успешно проверена", "success")
    return redirect(url_for("url_detail", id=id))
