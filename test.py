from datetime import datetime, timedelta
import pytest
from library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron
)

# def test_add_book_valid_input():
#     """Test adding a book with valid input."""
#     success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
    
#     assert success == True
#     assert "successfully added" in message.lower()

def test_add_book_invalid_isbn_too_short():
    """Test adding a book with ISBN too short."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    
    assert success == False
    assert "13 digits" in message

#Added test cases
def test_add_book_missing_title():
    """Test adding a book with missing/empty title."""
    success, message = add_book_to_catalog(
        "", "Author", "1234567890123", 5
    )
    assert success is False
    assert "title is required" in message.lower()

def test_add_book_invalid_total_copies():
    """Test adding a book with non-positive total copies."""
    success, message = add_book_to_catalog(
        "Book", "Author", "1234567890123", -1
    )
    assert success is False
    assert "positive integer" in message.lower()

def test_add_book_author_too_long():
    """Test adding a book with author name exceeding 100 characters."""

    long_author = "A" * 101
    success, message = add_book_to_catalog("Book", long_author, "1234567890123", 5)

    assert success is False
    assert "author must be less than 100" in message.lower()

def test_add_book_duplicate_isbn(monkeypatch):
    """Test adding a book with an ISBN that already exists."""

    monkeypatch.setattr("library_service.get_book_by_isbn", lambda isbn: {"isbn": isbn})

    success, message = add_book_to_catalog("Book", "Author", "1234567890123", 5)

    assert success is False
    assert "already exists" in message.lower()

# Add more test methods for each function and edge case. You can keep all your test in a separate folder named `tests`.

#tests for R3
def test_borrow_book_valid_input(monkeypatch):
    """Borrowing succeeds with valid patron ID and available copies."""

    monkeypatch.setattr("library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("library_service.get_patron_borrow_count", lambda patron_id: 2)
    monkeypatch.setattr("library_service.insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr("library_service.update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is True
    assert "successfully borrowed" in message.lower()


def test_borrow_book_invalid_patron_id():
    """Borrowing fails if patron ID is not 6 digits."""

    success, message = borrow_book_by_patron("12AB", 1)

    assert success is False
    assert "invalid patron id" in message.lower()


def test_borrow_book_not_found(monkeypatch):
    """Borrowing fails if book does not exist."""

    monkeypatch.setattr("library_service.get_book_by_id", lambda book_id: None)

    success, message = borrow_book_by_patron("123456", 99)

    assert success is False
    assert "book not found" in message.lower()


def test_borrow_book_not_available(monkeypatch):
    """Borrowing fails if no available copies remain."""

    monkeypatch.setattr("library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 0})

    success, message = borrow_book_by_patron("123456", 1)

    assert success is False
    assert "not available" in message.lower()


def test_borrow_book_patron_limit(monkeypatch):
    """Borrowing fails if patron already borrowed 5 books."""

    monkeypatch.setattr("library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("library_service.get_patron_borrow_count", lambda patron_id: 6)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is False
    assert "maximum borrowing limit" in message.lower()

#R4 test cases

def test_return_book_valid_input(monkeypatch):
    """Returning succeeds and updates available copies when patron had borrowed the book."""

    monkeypatch.setattr("library_service.get_borrow_record", lambda patron_id, book_id: {
        "id": 1,
        "patron_id": patron_id,
        "book_id": book_id,
        "borrow_date": datetime.now() - timedelta(days=10),
        "due_date": datetime.now() - timedelta(days=3),
        "return_date": None
    })
    monkeypatch.setattr("library_service.update_book_availability", lambda book_id, delta: True)
    monkeypatch.setattr("library_service.update_borrow_record_return_date", lambda record_id, return_date: True)
    monkeypatch.setattr("library_service.calculate_late_fee_for_book", lambda patron_id, book_id: {"fee_amount": 0.00, "days_overdue": 0})

    success, message = return_book_by_patron("123456", 1)

    assert success is True
    assert "successfully returned" in message.lower()


def test_return_book_invalid_patron_id():
    """Returning fails if patron ID is invalid."""

    success, message = return_book_by_patron("12AB", 1)

    assert success is False
    assert "invalid patron id" in message.lower()


def test_return_book_not_borrowed(monkeypatch):
    """Returning fails if patron never borrowed this book."""

    monkeypatch.setattr("library_service.get_borrow_record", lambda patron_id, book_id: None)

    success, message = return_book_by_patron("123456", 1)

    assert success is False
    assert "not borrowed" in message.lower()


def test_return_book_updates_late_fee(monkeypatch):
    """Returning should include late fee if overdue."""

    borrow_date = datetime.now() - timedelta(days=25)  # overdue
    due_date = borrow_date + timedelta(days=14)

    monkeypatch.setattr("library_service.get_borrow_record", lambda patron_id, book_id: {
        "id": 1,
        "patron_id": patron_id,
        "book_id": book_id,
        "borrow_date": borrow_date,
        "due_date": due_date,
        "return_date": None
    })
    monkeypatch.setattr("library_service.update_book_availability", lambda book_id, delta: True)
    monkeypatch.setattr("library_service.update_borrow_record_return_date", lambda record_id, return_date: True)
    monkeypatch.setattr("library_service.calculate_late_fee_for_book", lambda patron_id, book_id: {"fee_amount": 7.50, "days_overdue": 11})

    success, message = return_book_by_patron("123456", 1)

    assert success is True
    assert "late fee" in message.lower()
    assert "7.50" in message  # formatted to 2 decimals

#R5
