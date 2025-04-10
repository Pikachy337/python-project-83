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


def _check_existing_url(domain):
    """Check if URL already exists in database."""
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM urls WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
                (domain,),
            )
            return cur.fetchone()
    except Exception as e:
        app.logger.error(f"Database error when checking URL: {str(e)}")
        return None


def _insert_new_url(domain):
    """Insert new URL into database."""
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO urls (name) VALUES (%s) RETURNING id",
                (domain,)
            )
            return cur.fetchone()[0]
    except Exception as e:
        app.logger.error(f"Database error when inserting URL: {str(e)}")
        raise


@app.route("/urls", methods=["POST"])
def add_url():
    """Handle URL submission."""
    url = request.form.get("url", "").strip()

    try:
        normalized_url = validate_and_normalize_url(url)
        domain = urlparse(normalized_url).netloc.lower()
    except ValueError as e:
        flash(str(e), "danger")
        return render_template("index.html", error_message=str(e)), 422

    existing = _check_existing_url(domain)
    if existing is None:
        flash("Ошибка базы данных", "danger")
        return redirect(url_for("index"))

    if existing:
        flash("Страница уже существует", "info")
        return redirect(url_for("url_detail", id=existing[0]))

    try:
        new_id = _insert_new_url(domain)
        flash("Страница успешно добавлена", "success")
        return redirect(url_for("url_detail", id=new_id))
    except Exception:
        flash("Ошибка базы данных", "danger")
        return redirect(url_for("index"))


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
    """Perform website availability and SEO check for given URL ID."""
    with get_db() as conn, conn.cursor() as cur:
        cur.execute("SELECT name FROM urls WHERE id = %s", (id,))
        url = cur.fetchone()

        if not url:
            flash("URL не найден!", "danger")
            return redirect(url_for("urls"))

        url = url[0]
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = "http://" + url

        try:
            response = requests.get(url, allow_redirects=True, timeout=10)
            response.raise_for_status()
        except RequestException:
            flash("Произошла ошибка при проверке", "danger")
            return redirect(url_for("url_detail", id=id))

        seo_data = _get_seo_data(response.text)
        _save_check_results(conn, id, response.status_code, seo_data)

    return redirect(url_for("url_detail", id=id))


def _get_seo_data(html_content):
    """
    Extract SEO data from HTML content.
    Returns dict with h1, title and description
    (empty strings if parsing fails).
    """
    try:
        return parse_seo_data(html_content)
    except Exception as e:
        app.logger.error(f"Ошибка парсинга SEO данных: {str(e)}")
        return {'h1': '', 'title': '', 'description': ''}


def _save_check_results(conn, url_id, status_code, seo_data):
    """
    Save URL check results to database.
    Handles database errors and shows appropriate flash messages.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO url_checks
                (url_id, status_code, h1, title, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    url_id,
                    status_code,
                    seo_data['h1'],
                    seo_data['title'],
                    seo_data['description'],
                    datetime.now(),
                ),
            )
        conn.commit()
        flash("Страница успешно проверена", "success")
    except Exception as e:
        conn.rollback()
        flash("Произошла ошибка при проверке", "danger")
        app.logger.error(f"Database error: {str(e)}")
