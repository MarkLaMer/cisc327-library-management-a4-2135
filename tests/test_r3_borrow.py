'''
author: Mark Nistor
title: R3 — Book Borrowing Interface (Business-Logic Tests)

These tests cover the business logic in `library_service.borrow_book_by_patron`.
We monkeypatch DB-layer helpers so no real database is touched.

R3 verifies:
- Accepts patron_id & book_id (form passes them; here we call the service directly)
- Patron ID validation (exactly 6 digits)
- Book availability & borrowing limit (max 5 books)
- Creates borrowing record and decrements available copies
- Returns appropriate success/error messages
'''

import pytest
from services.library_service import borrow_book_by_patron


def _stub_book(id: int = 1, title: str = "Any", available: int = 2, total: int = 3) -> dict:
    """
    Create a minimal book dict like the DB would return.

    Args:
        id: Book ID
        title: Book title (for message formatting)
        available: available_copies the service should see
        total: total_copies (not used by the service here, but kept realistic)

    Returns:
        dict shaped like rows the DB layer returns.
    """
    return {
        "id": id,
        "title": title,
        "isbn": "1234567890123",
        "available_copies": available,
        "total_copies": total,
    }


def test_borrow_happy_path(monkeypatch):
    """
    Happy path:
    - Valid 6-digit patron ID
    - Book exists and has available copies
    - Patron below limit
    Expect:
    - insert_borrow_record called
    - update_book_availability(book_id, -1) called
    - Success message mentioning "successfully borrowed"
    """
    # Make DB helpers return "book exists, 2 available" and "3 already borrowed"
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: _stub_book(id=10, available=2))
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 3)

    # Capture interactions with the DB layer
    called = {}

    def fake_insert(patron_id, book_id, borrow_date, due_date):
        called["insert"] = (patron_id, book_id, borrow_date, due_date)
        return True

    def fake_update(book_id, delta):
        called["update"] = (book_id, delta)
        return True

    monkeypatch.setattr("services.library_service.insert_borrow_record", fake_insert)
    monkeypatch.setattr("services.library_service.update_book_availability", fake_update)

    ok, msg = borrow_book_by_patron("123456", 10)

    assert ok is True
    assert "successfully borrowed" in msg.lower()
    assert called["update"] == (10, -1)                # availability decremented
    assert called["insert"][0] == "123456"             # patron ID recorded
    assert called["insert"][1] == 10                   # book ID recorded


@pytest.mark.parametrize(
    "bad_patron",
    ["", "12345", "abcdef", "12345a", " 123456", "1234567"]
)
def test_borrow_invalid_patron_id(monkeypatch, bad_patron):
    """
    Patron ID must be exactly 6 digits.
    Validation should fail before any DB calls matter.
    """
    # These stubs won't be used because validation fails first
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book())
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda _: 0)

    ok, msg = borrow_book_by_patron(bad_patron, 1)
    assert ok is False
    assert "6 digits" in msg.lower()


def test_borrow_book_not_found(monkeypatch):
    """
    If the requested book doesn't exist, return a clear error.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: None)

    ok, msg = borrow_book_by_patron("123456", 999)
    assert ok is False
    assert "book not found" in msg.lower()


def test_borrow_book_unavailable(monkeypatch):
    """
    If the book has 0 available copies, refuse the borrow.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book(available=0))

    ok, msg = borrow_book_by_patron("123456", 1)
    assert ok is False
    assert "not available" in msg.lower()


# @pytest.mark.xfail(reason="Spec: max 5; implementation only blocks when count > 5")
def test_borrow_limit_reached_at_5_should_fail(monkeypatch):
    """
    Spec says 'max 5' → if patron already has 5, a new borrow should be blocked.
    Current code uses `> 5`, so this test documents the off-by-one defect.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book(available=1))
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda _: 5)

    # These would not be called if validation were correct
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *a, **k: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *a, **k: True)

    ok, msg = borrow_book_by_patron("123456", 1)
    assert ok is False
    assert "maximum borrowing limit of 5" in msg.lower()


def test_borrow_limit_over_5_fails(monkeypatch):
    """
    If the patron is already over the limit (e.g., 6), the service must refuse.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book(available=1))
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda _: 6)

    ok, msg = borrow_book_by_patron("123456", 1)
    assert ok is False
    assert "maximum borrowing limit of 5" in msg.lower()


def test_borrow_db_insert_failure(monkeypatch):
    """
    If creating the borrow record fails, return a DB error message
    and do not attempt to decrement availability afterwards.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book(available=1))
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda _: 0)

    # Simulate DB failing on record insert
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *a, **k: False)

    ok, msg = borrow_book_by_patron("123456", 1)
    assert ok is False
    assert "database error" in msg.lower()


def test_borrow_db_update_availability_failure(monkeypatch):
    """
    If the availability update fails after creating the record,
    surface a DB error message to the caller.
    """
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda _: _stub_book(available=1))
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda _: 0)

    # Insert succeeds, but availability update fails
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *a, **k: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *a, **k: False)

    ok, msg = borrow_book_by_patron("123456", 1)
    assert ok is False
    assert "database error" in msg.lower()
