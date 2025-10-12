'''
author: Mark Nistor
title: R6 — Book Search (Business-Logic Tests)

These tests cover:
- Service: library_service.search_books_in_catalog(search_term, search_type)

R6 verifies:
- type=title → partial, case-insensitive match on title
- type=author → partial, case-insensitive match on author
- type=isbn → exact match on ISBN
- Partial ISBN should not match (must be exact)
- Results shaped like catalog items

Note: Service not implemented yet; expectation tests are xfail.
'''

import pytest
from library_service import search_books_in_catalog


BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "isbn": "9780132350884",
     "available_copies": 1, "total_copies": 3},
    {"id": 2, "title": "Fluent Python", "author": "Luciano Ramalho", "isbn": "9781492056355",
     "available_copies": 0, "total_copies": 2},
    {"id": 3, "title": "The Pragmatic Programmer", "author": "Andrew Hunt", "isbn": "9780201616224",
     "available_copies": 2, "total_copies": 2},
]


def _patch_all_books(monkeypatch):
    # Whatever the service calls to read books; try both likely spots.
    try:
        import routes.catalog_routes as cr
        monkeypatch.setattr(cr, "get_all_books", lambda: BOOKS)
    except Exception:
        import database as db
        monkeypatch.setattr(db, "get_all_books", lambda: BOOKS)


def test_current_placeholder_returns_list(monkeypatch):
    """Keep a simple sanity check for the current (empty) placeholder."""
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("py", "title")
    assert isinstance(out, list)


# @pytest.mark.xfail(reason="Service not implemented yet: partial, case-insensitive title match")
def test_search_title_partial_case_insensitive(monkeypatch):
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("python", "title")   # should match "Fluent Python"
    assert any(b["id"] == 2 for b in out)


# @pytest.mark.xfail(reason="Service not implemented yet: partial, case-insensitive author match")
def test_search_author_partial_case_insensitive(monkeypatch):
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("martin", "author")  # "Robert C. Martin"
    assert any(b["id"] == 1 for b in out)


# @pytest.mark.xfail(reason="Service not implemented yet: ISBN exact match only")
def test_search_isbn_exact(monkeypatch):
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("9780201616224", "isbn")  # exact
    assert len(out) == 1 and out[0]["id"] == 3


# @pytest.mark.xfail(reason="Service not implemented yet: partial ISBN should not match")
def test_search_isbn_partial_no_match(monkeypatch):
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("978020", "isbn")  # partial → should not match
    assert out == []


# @pytest.mark.xfail(reason="Service not implemented yet: unknown type returns []")
def test_search_unknown_type_returns_empty(monkeypatch):
    _patch_all_books(monkeypatch)
    out = search_books_in_catalog("anything", "publisher")
    assert out == []



# Additional tests - A2


# a few books I like for testing purposes
BOOKS_R6 = [
    {"id": 1, "title": "Sense and Sensibility", "author": "Jane Austen",  "isbn": "9876543212345", "available_copies": 2, "total_copies": 2},
    {"id": 2, "title": "The Alchemist",         "author": "Paulo Coelho", "isbn": "9876543217894", "available_copies": 1, "total_copies": 1},
    {"id": 3, "title": "Les Misérables",        "author": "Victor Hugo",  "isbn": "9876543216543", "available_copies": 1, "total_copies": 1},
]

def _patch_conn(monkeypatch):
    """
    Monkeypatch library_service.get_db_connection with a tiny function-based version.
    """
    import library_service as svc
    def make_cursor(rows):
        def cur(): pass
        cur.fetchall = lambda: rows
        cur.fetchone  = lambda: (rows[0] if rows else None)
        return cur
    
    # Emulate the few SQL patterns used by search_books_in_catalog
    def execute(sql, params=()):
        q = " ".join(sql.split()).upper()
        if q.startswith("SELECT * FROM BOOKS ORDER BY TITLE"):
            return make_cursor(sorted(BOOKS_R6, key=lambda r: r["title"]))
        if "WHERE TITLE LIKE" in q:
            needle = params[0].strip("%").lower()
            return make_cursor(sorted([r for r in BOOKS_R6 if needle in r["title"].lower()], key=lambda r: r["title"]))
        if "WHERE AUTHOR LIKE" in q:
            needle = params[0].strip("%").lower()
            return make_cursor(sorted([r for r in BOOKS_R6 if needle in r["author"].lower()], key=lambda r: (r["author"], r["title"])))
        if "WHERE ISBN =" in q:
            return make_cursor([r for r in BOOKS_R6 if r["isbn"] == params[0]])
        return make_cursor([])
    
    # Minimal connection with execute
    def conn(): pass
    conn.execute = execute
    conn.close = lambda: None
    monkeypatch.setattr(svc, "get_db_connection", lambda: conn)

# def test_title_partial_case_insensitive_min(monkeypatch):
#     """
#     Case-insensitive match (e.g. "sense" to "Sense and Sensibility")
#     """
#     _patch_conn(monkeypatch)
#     import library_service as svc
#     out = svc.search_books_in_catalog("sense", "title")
#     assert any(r["title"] == "Sense and Sensibility" for r in out)

def test_isbn_exact_vs_partial_min(monkeypatch):
    """
    Test that partial ISBN must not match
    """
    _patch_conn(monkeypatch)
    import library_service as svc
    exact   = svc.search_books_in_catalog("9876543216543", "isbn")
    partial = svc.search_books_in_catalog("9876543", "isbn")
    assert len(exact) == 1 and exact[0]["title"] == "Les Misérables"
    assert partial == []
