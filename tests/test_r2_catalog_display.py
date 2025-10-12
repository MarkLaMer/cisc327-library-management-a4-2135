'''
author: Mark Nistor
title: R2 — Catalog Display (Route/UI Tests)

These tests cover the /catalog page rendering.
We monkeypatch the book fetcher so no real DB is used.

R2 verifies:
- GET /catalog returns 200 and HTML
- Table shows headers: ID, Title, Author, ISBN, Availability, Actions
- Each row shows: id, title, author, isbn
- Availability renders "X/Y Available" when copies remain, or "Not Available" otherwise
- Borrow form appears only when available (POST, hidden book_id, patron_id with 6-digit pattern)
- Empty state shows "No books in catalog" and an "Add New Book" link
'''

import pytest
import re

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

# We rely on the `client` fixture in tests/conftest.py

def test_catalog_headers_and_rows(monkeypatch, client):
    """Headers match template; rows show all required fields."""
    books = [
        {"id": 1, "title": "Book One", "author": "Author A",
         "isbn": "1234567890123", "available_copies": 2, "total_copies": 5},
        {"id": 2, "title": "Book Two", "author": "Author B",
         "isbn": "9876543210987", "available_copies": 0, "total_copies": 3},
    ]
    _patch_get_all_books(monkeypatch, books)

    resp = client.get("/catalog")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"

    html = resp.get_data(as_text=True)

    # Exact headers from your template
    for header in ("ID", "Title", "Author", "ISBN", "Availability", "Actions"):
        assert f"<th>{header}</th>" in html

    # Rows show fields
    for b in books:
        assert f">{b['id']}<" in html
        assert b["title"] in html
        assert b["author"] in html
        assert b["isbn"] in html

    # Availability formatting per template
    assert 'class="status-available"' in html and "2/5 Available" in html
    assert 'class="status-unavailable"' in html and "Not Available" in html

def test_borrow_form_present_for_available_book(monkeypatch, client):
    """Available book shows the Borrow form with correct inputs/constraints."""
    books = [
        {"id": 42, "title": "Available", "author": "A",
         "isbn": "1111111111111", "available_copies": 1, "total_copies": 2},
    ]
    _patch_get_all_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)

    # Borrow button text
    assert ">Borrow<" in html
    # Hidden book_id present with correct value
    assert 'type="hidden"' in html and 'name="book_id"' in html and 'value="42"' in html
    # Patron input constraints from template
    assert 'name="patron_id"' in html
    assert 'pattern="[0-9]{6}"' in html
    assert 'maxlength="6"' in html
    assert "required" in html
    # Form should be POST
    assert re.search(r'<form[^>]*method="POST"', html, flags=re.IGNORECASE)

def test_no_borrow_form_when_unavailable(monkeypatch, client):
    """Unavailable book renders 'Not Available' and no Borrow form/button."""
    books = [
        {"id": 7, "title": "None", "author": "N",
         "isbn": "2222222222222", "available_copies": 0, "total_copies": 3},
    ]
    _patch_get_all_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)
    assert "Not Available" in html
    # No borrow controls when unavailable
    assert "Borrow</button>" not in html
    assert "<form" not in html

def test_empty_state(monkeypatch, client):
    """Empty catalog shows the empty-state message and the Add New Book link."""
    _patch_get_all_books(monkeypatch, [])

    html = client.get("/catalog").get_data(as_text=True)
    assert "No books in catalog" in html
    assert "Add New Book" in html
