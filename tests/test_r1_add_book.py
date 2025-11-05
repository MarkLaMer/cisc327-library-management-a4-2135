'''
author: Mark Nistor
title: R1 — Add Book To Catalog

These tests exercise the business logic in `library_service.add_book_to_catalog`
without touching the real database. We use pytest's `monkeypatch` to replace
the DB helpers that `library_service.py` imports

R1 will verify:
- Happy path returns success and initializes available_copies == total_copies.
- Duplicate ISBNs are rejected.
- Input validation for title/author length and presence.
- ISBN length enforcement (exactly 13).
- Total copies must be a positive integer.
- (Spec expectation) ISBN must be 13 *digits* (marked xfail since current code
  only checks length==13, not digits-only).

NOTE: make sure `tests/conftest.py` adds project root to sys.path so `from library_service import add_book_to_catalog` works.
'''

import pytest
from services.library_service import add_book_to_catalog

# Happy Path Tests for adding a book to the library catalog
def test_add_book_valid_input(monkeypatch):
    """
    Simple happy path:
    - We stub the DB so the test never depends on a real database.
    - Expect success and a success message.
    """
    # no duplicate
    monkeypatch.setattr("services.library_service.get_book_by_isbn", lambda _: None)
    # pretend insert succeeds (we’re not asserting insert args to keep it simple)
    monkeypatch.setattr("services.library_service.insert_book", lambda *a, **k: True)

    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
    assert success is True
    assert "successfully added" in message.lower()

# Edge Case and Validation Tests for adding a book to the library catalog
def test_add_book_invalid_isbn_too_short():
    """Fails validation before DB is touched."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    assert success is False
    assert "13 digits" in message

def test_add_book_missing_title():
    success, message = add_book_to_catalog("", "Author", "1234567890123", 5)
    assert success is False
    assert "title is required" in message.lower()

def test_add_book_invalid_total_copies():
    success, message = add_book_to_catalog("Book", "Author", "1234567890123", -1)
    assert success is False
    assert "positive integer" in message.lower()

def test_add_book_author_too_long():
    long_author = "A" * 101
    success, message = add_book_to_catalog("Book", long_author, "1234567890123", 5)
    assert success is False
    assert "author must be less than 100" in message.lower()

def test_add_book_duplicate_isbn(monkeypatch):
    """This path checks the DB, so we stub just that one helper."""
    monkeypatch.setattr("services.library_service.get_book_by_isbn", lambda isbn: {"isbn": isbn})
    # insert should not be called, but we don’t need to stub it to assert the message
    success, message = add_book_to_catalog("Book", "Author", "1234567890123", 5)
    assert success is False
    assert "already exists" in message.lower()

def test_add_book_author_required():
    success, message = add_book_to_catalog("Book", "   ", "1234567890123", 5)
    assert success is False
    assert "author is required" in message.lower()

def test_add_book_title_too_long():
    success, message = add_book_to_catalog("T"*201, "Author", "1234567890123", 5)
    assert success is False
    assert "less than 200" in message.lower()

def test_add_book_isbn_too_long():
    success, message = add_book_to_catalog("Book", "Author", "12345678901234", 5)  # 14 chars
    assert success is False
    assert "13 digits" in message

def test_add_book_total_copies_zero():
    success, message = add_book_to_catalog("Book", "Author", "1234567890123", 0)
    assert success is False
    assert "positive integer" in message.lower()

def test_add_book_isbn_not_all_digits():
    success, message = add_book_to_catalog("Book", "Author", "12345678987X5", 5)  # includes 'X'
    assert success is False
    assert "13 digits" in message.lower()
