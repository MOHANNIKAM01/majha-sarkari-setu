import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort, Response
)

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    def get_db():
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con

    def init_db():
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category_slug TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                created_at TEXT NOT NULL,
                is_published INTEGER NOT NULL DEFAULT 1
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        existing = {r["slug"] for r in cur.execute("SELECT slug FROM categories").fetchall()}
        seeds = [
            ("Jobs", "job"),
            ("Results", "result"),
            ("Schemes", "scheme"),
            ("Exam Cutoffs", "examcutoff"),
            ("Current Affairs", "currentaffairs"),
        ]
        for name, slug in seeds:
            if slug not in existing:
                cur.execute(
                    "INSERT OR IGNORE INTO categories (name, slug) VALUES (?,?)",
                    (name, slug)
                )

        con.commit()
        con.close()

    init_db()

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("admin_login", next=request.path))
            return fn(*args, **kwargs)
        return wrapper

    @app.context_processor
    def inject_globals():
        return {
            "site_name": "Majha Sarkari Setu",
            "year": datetime.now().year,
        }

    # ---------------- PUBLIC ----------------
    @app.get("/")
    def home():
        con = get_db()

        def latest_for(slug, limit=6):
            return con.execute(
                """SELECT id, title, summary, created_at
                   FROM posts
                   WHERE category_slug=? AND is_published=1
                   ORDER BY id DESC LIMIT ?""",
                (slug, limit)
            ).fetchall()

        jobs = latest_for("job", 8)
        results = latest_for("result", 6)
        schemes = latest_for("scheme", 6)

        latest = con.execute(
            """SELECT id, title, category_slug, summary, created_at
               FROM posts
               WHERE is_published=1
               ORDER BY id DESC LIMIT 10"""
        ).fetchall()
        con.close()

        return render_template(
            "index.html",
            jobs=jobs,
            results=results,
            schemes=schemes,
            latest=latest,
        )

    @app.get("/category/<slug>")
    def category(slug):
        con = get_db()
        cat = con.execute("SELECT name, slug FROM categories WHERE slug=?", (slug,)).fetchone()
        if not cat:
            abort(404)

        posts = con.execute(
            """SELECT id, title, summary, created_at
               FROM posts
               WHERE category_slug=? AND is_published=1
               ORDER BY id DESC""",
            (slug,)
        ).fetchall()
        con.close()
        return render_template("category.html", category=cat, posts=posts)

    @app.get("/post/<int:post_id>")
    def post(post_id):
        con = get_db()
        p = con.execute(
            "SELECT * FROM posts WHERE id=? AND is_published=1", (post_id,)
        ).fetchone()
        if not p:
            abort(404)

        cat = con.execute(
            "SELECT name, slug FROM categories WHERE slug=?", (p["category_slug"],)
        ).fetchone()
        con.close()
        return render_template("post.html", post=p, category=cat)

    @app.get("/search")
    def search():
        q = (request.args.get("q") or "").strip()
        con = get_db()
        posts = []
        if q:
            like = f"%{q}%"
            posts = con.execute(
                """SELECT id, title, summary, created_at, category_slug
                   FROM posts
                   WHERE is_published=1
                   AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)
                   ORDER BY id DESC""",
                (like, like, like),
            ).fetchall()
        con.close()
        return render_template("search.html", q=q, posts=posts)

    # ---------------- CONTACT ----------------
    @app.get("/contact")
    def contact():
        return render_template("contact.html")

    @app.post("/contact")
    def contact_post():
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        message = request.form.get("message","").strip()

        if not (name and email and message):
            flash("All fields required.", "danger")
            return redirect(url_for("contact"))

        con = get_db()
        con.execute(
            "INSERT INTO contact_messages (name,email,message,created_at) VALUES (?,?,?,?)",
            (name, email, message, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        con.commit()
        con.close()

        flash("Message sent successfully ✅", "success")
        return redirect(url_for("contact"))

    # ---------------- SITEMAP ----------------
    @app.get("/sitemap.xml")
    def sitemap():
        con = get_db()
        base_url = request.url_root.rstrip("/")

        urls = []
        urls.append(f"{base_url}/")

        categories = con.execute("SELECT slug FROM categories").fetchall()
        for c in categories:
            urls.append(f"{base_url}/category/{c['slug']}")

        posts = con.execute("SELECT id FROM posts WHERE is_published=1").fetchall()
        for p in posts:
            urls.append(f"{base_url}/post/{p['id']}")

        con.close()

        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for url in urls:
            xml.append("  <url>")
            xml.append(f"    <loc>{url}</loc>")
            xml.append("  </url>")
        xml.append("</urlset>")

        return Response("\n".join(xml), mimetype="application/xml")

    # ---------------- ROBOTS ----------------
    @app.get("/robots.txt")
    def robots():
        base_url = request.url_root.rstrip("/")
        txt = f"""User-agent: *
Allow: /

Disallow: /admin
Disallow: /admin/

Sitemap: {base_url}/sitemap.xml
"""
        return Response(txt, mimetype="text/plain")

    # ---------------- ERRORS ----------------
    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
