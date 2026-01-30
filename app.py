\
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort
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

        # seed categories
        existing = {r["slug"] for r in cur.execute("SELECT slug FROM categories").fetchall()}
        seeds = [("Jobs", "job"), ("Results", "result"), ("Schemes", "scheme")]
        for name, slug in seeds:
            if slug not in existing:
                cur.execute("INSERT OR IGNORE INTO categories (name, slug) VALUES (?,?)", (name, slug))

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

    @app.get("/")
    def home():
        con = get_db()
        cats = con.execute("SELECT name, slug FROM categories ORDER BY id").fetchall()

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
        return render_template("index.html", cats=cats, jobs=jobs, results=results, schemes=schemes, latest=latest)

    @app.get("/category/<slug>")
    def category(slug):
        con = get_db()
        cat = con.execute("SELECT name, slug FROM categories WHERE slug=?", (slug,)).fetchone()
        if not cat:
            con.close()
            abort(404)
        posts = con.execute(
            """SELECT id, title, summary, created_at
               FROM posts WHERE category_slug=? AND is_published=1
               ORDER BY id DESC""",
            (slug,)
        ).fetchall()
        con.close()
        return render_template("category.html", category=cat, posts=posts)

    @app.get("/post/<int:post_id>")
    def post(post_id: int):
        con = get_db()
        p = con.execute("SELECT * FROM posts WHERE id=? AND is_published=1", (post_id,)).fetchone()
        if not p:
            con.close()
            abort(404)
        cat = con.execute("SELECT name, slug FROM categories WHERE slug=?", (p["category_slug"],)).fetchone()
        con.close()
        return render_template("post.html", post=p, category=cat)

    @app.get("/search")
    def search():
        q = (request.args.get("q") or "").strip()
        con = get_db()
        cats = con.execute("SELECT name, slug FROM categories ORDER BY id").fetchall()
        posts = []
        if q:
            like = f"%{q}%"
            posts = con.execute(
                """SELECT id, title, summary, created_at, category_slug
                   FROM posts
                   WHERE is_published=1 AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)
                   ORDER BY id DESC""",
                (like, like, like)
            ).fetchall()
        con.close()
        return render_template("search.html", q=q, posts=posts, cats=cats)

    # ---------------- Admin ----------------
    @app.get("/admin/login")
    def admin_login():
        return render_template("admin_login.html", next=request.args.get("next", "/admin"))

    @app.post("/admin/login")
    def admin_login_post():
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        next_url = request.form.get("next") or "/admin"

        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin_password:
            flash("ADMIN_PASSWORD env var set केलेला नाही. सुरक्षा साठी admin login बंद आहे.", "danger")
            return redirect(url_for("admin_login"))

        if username == "admin" and password == admin_password:
            session["admin"] = True
            flash("Admin login successful ✅", "success")
            return redirect(next_url)
        flash("Wrong username/password ❌", "danger")
        return redirect(url_for("admin_login"))

    @app.get("/admin/logout")
    def admin_logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("home"))

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        con = get_db()
        cats = con.execute("SELECT name, slug FROM categories ORDER BY id").fetchall()
        posts = con.execute(
            """SELECT id, title, category_slug, created_at, is_published
               FROM posts ORDER BY id DESC LIMIT 50"""
        ).fetchall()
        con.close()
        return render_template("admin.html", cats=cats, posts=posts)

    @app.post("/admin/category/add")
    @admin_required
    def admin_add_category():
        name = (request.form.get("name") or "").strip()
        slug = (request.form.get("slug") or "").strip().lower()
        if not name or not slug:
            flash("Category name + slug required.", "danger")
            return redirect(url_for("admin_dashboard"))
        con = get_db()
        try:
            con.execute("INSERT INTO categories (name, slug) VALUES (?,?)", (name, slug))
            con.commit()
            flash("Category added ✅", "success")
        except sqlite3.IntegrityError:
            flash("हा slug/name आधीच आहे.", "danger")
        finally:
            con.close()
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/post/add")
    @admin_required
    def admin_add_post():
        title = (request.form.get("title") or "").strip()
        category_slug = (request.form.get("category_slug") or "").strip()
        summary = (request.form.get("summary") or "").strip()
        content = (request.form.get("content") or "").strip()
        source_url = (request.form.get("source_url") or "").strip() or None

        if not (title and category_slug and summary and content):
            flash("Title, Category, Summary, Content required.", "danger")
            return redirect(url_for("admin_dashboard"))

        con = get_db()
        con.execute(
            """INSERT INTO posts (title, category_slug, summary, content, source_url, created_at, is_published)
               VALUES (?,?,?,?,?,?,1)""",
            (title, category_slug, summary, content, source_url, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        con.commit()
        con.close()
        flash("Post added ✅", "success")
        return redirect(url_for("admin_dashboard"))

    @app.get("/admin/post/<int:post_id>/edit")
    @admin_required
    def admin_edit_post(post_id: int):
        con = get_db()
        p = con.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        cats = con.execute("SELECT name, slug FROM categories ORDER BY id").fetchall()
        con.close()
        if not p:
            abort(404)
        return render_template("admin_edit.html", post=p, cats=cats)

    @app.post("/admin/post/<int:post_id>/edit")
    @admin_required
    def admin_edit_post_post(post_id: int):
        title = (request.form.get("title") or "").strip()
        category_slug = (request.form.get("category_slug") or "").strip()
        summary = (request.form.get("summary") or "").strip()
        content = (request.form.get("content") or "").strip()
        source_url = (request.form.get("source_url") or "").strip() or None
        is_published = 1 if request.form.get("is_published") == "1" else 0

        con = get_db()
        con.execute(
            """UPDATE posts
               SET title=?, category_slug=?, summary=?, content=?, source_url=?, is_published=?
               WHERE id=?""",
            (title, category_slug, summary, content, source_url, is_published, post_id)
        )
        con.commit()
        con.close()
        flash("Post updated ✅", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/post/<int:post_id>/delete")
    @admin_required
    def admin_delete_post(post_id: int):
        con = get_db()
        con.execute("DELETE FROM posts WHERE id=?", (post_id,))
        con.commit()
        con.close()
        flash("Post deleted 🗑️", "info")
        return redirect(url_for("admin_dashboard"))

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app

app = create_app()

if __name__ == "__main__":
    # debug off by default for safer local use; change to True if you want
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
