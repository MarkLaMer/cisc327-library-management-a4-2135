"""
author: Mark Nistor
title: R2 — Catalog Display

R2 verifies:
- GET /catalog returns 200 and HTML
- Columns: Book ID/Title/Author/ISBN + Available/Total
- "Borrow" is shown for available books, hidden when none available
"""

import pytest

# --- helper: patch the data source the route uses --------------------------
def _patch_get_all_books(monkeypatch, books):
    """
    Patch the function the /catalog route uses to fetch books.
    Tries routes.catalog_routes.get_all_books first; falls back to database.get_all_books.
    """
    try:
        import routes.catalog_routes as cr
        monkeypatch.setattr(cr, "get_all_books", lambda: books)
        return
    except Exception:
        pass
    import database as db
    monkeypatch.setattr(db, "get_all_books", lambda: books)

# --- client fixture --------------------------------------------------------
@pytest.fixture
def client():
    """Flask test client (uses your app factory)."""
    from app import create_app  # change if your factory name differs
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

# --- tests -----------------------------------------------------------------
def test_catalog_basic_table_and_rows(monkeypatch, client):
    """Page renders 200 + shows column labels and book rows."""
    books = [
        {"id": 1, "title": "Book One", "author": "Author A",
         "isbn": "1234567890123", "available_copies": 2, "total_copies": 5},
        {"id": 2, "title": "Book Two", "author": "Author B",
         "isbn": "9876543210987", "available_copies": 0, "total_copies": 3},
    ]
    _patch_get_all_books(monkeypatch, books)

    resp = client.get("/catalog")  # change path if yours differs
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"

    html = resp.get_data(as_text=True)
    # headers/labels (keep loose to avoid template brittleness)
    for label in ("Title", "Author", "ISBN", "Available", "Total"):
        assert label in html

    # rows
    for b in books:
        assert str(b["id"]) in html
        assert b["title"] in html
        assert b["author"] in html
        assert b["isbn"] in html
        assert str(b["available_copies"]) in html
        assert str(b["total_copies"]) in html

def test_borrow_button_shown_when_any_available(monkeypatch, client):
    """At least one available book → 'Borrow' appears somewhere on the page."""
    books = [
        {"id": 1, "title": "Available Book", "author": "Author A",
         "isbn": "1234567890123", "available_copies": 2, "total_copies": 5},
        {"id": 2, "title": "Unavailable Book", "author": "Author B",
         "isbn": "9876543210987", "available_copies": 0, "total_copies": 3},
    ]
    _patch_get_all_books(monkeypatch, books)

    resp = client.get("/catalog")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Borrow" in html  # keep assertion simple & template-agnostic

def test_borrow_button_hidden_when_none_available(monkeypatch, client):
    """No available books → no 'Borrow' action should appear."""
    books = [
        {"id": 1, "title": "A", "author": "X",
         "isbn": "1111111111111", "available_copies": 0, "total_copies": 1},
        {"id": 2, "title": "B", "author": "Y",
         "isbn": "2222222222222", "available_copies": 0, "total_copies": 3},
    ]
    _patch_get_all_books(monkeypatch, books)

    resp = client.get("/catalog")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Borrow" not in html
