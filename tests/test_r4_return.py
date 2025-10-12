"""
author: Mark Nistor
title: R4 — Book Return Processing (Business-Logic Tests)

These tests target `library_service.return_book_by_patron(patron_id, book_id)`.
We monkeypatch DB-layer helpers and time so no real database or clock is used.

R4 verifies:
- Accepts patron_id & book_id (form provides them; here we call the service directly)
- Validates patron ID (exactly 6 digits)
- Verifies the book was borrowed by the patron
- On success: records return date, increments available copies, and returns any late fee owed
- Returns appropriate success/error messages

Notes:
- Current implementation returns "not yet implemented". We include one test that
  asserts that message (to reflect current state), and mark the behavior tests
  as xfail until R4 is implemented.
"""


import pytest
import library_service as svc


# ----------------- helpers -----------------

def _borrowing_record(
    rec_id=1,
    patron_id="123456",
    book_id=10,
    borrow_date=None,
    due_date=None,
    return_date=None,
    title="Any Book",
):
    """Minimal shape used by some tests; only 'due_date' is read by service (and we stub fee anyway)."""
    # We don't use real datetimes; store strings so code paths that stringify won't break.
    return {
        "id": rec_id,
        "patron_id": patron_id,
        "book_id": book_id,
        "borrow_date": borrow_date or "2025-01-01T10:00:00",
        "due_date": due_date or "2025-01-15T10:00:00",
        "return_date": return_date,  # None means active; any string means already returned (but service never sees it)
        "title": title,
    }


def _patch_lookup_record(monkeypatch, record):
    """
    Patch the function the service uses to fetch the active borrow record.
    Your code uses get_borrow_record(patron_id, book_id).
    """
    monkeypatch.setattr(svc, "get_borrow_record", lambda pid, bid: record)


def _patch_book_exists(monkeypatch, title="Any Book", available_copies=0):
    """Stub a book row so the flow proceeds past 'Book not found'."""
    monkeypatch.setattr(
        svc,
        "get_book_by_id",
        lambda bid: {"id": bid, "title": title, "available_copies": available_copies},
    )


# ----------------- tests (names preserved) -----------------

def test_current_status_not_implemented(monkeypatch):
    """
    Original 'not implemented' smoke test.
    R4 is implemented now, so we keep this function name but change it to a success smoke test.
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, _borrowing_record())
    # Fee calc stub → avoid any time math
    monkeypatch.setattr(
        svc,
        "calculate_late_fee_for_book",
        lambda *a, **k: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"},
    )
    # DB updates succeed
    monkeypatch.setattr(svc, "update_borrow_record_return_date", lambda *_: True)
    monkeypatch.setattr(svc, "update_book_availability", lambda *_: True)

    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is True
    assert "book returned" in msg.lower()


@pytest.mark.parametrize("bad_pid", ["", "12345", "abcdef", "12345a", " 123456", "1234567"])
def test_return_invalid_patron_id(monkeypatch, bad_pid):
    ok, msg = svc.return_book_by_patron(bad_pid, 10)
    assert ok is False and "6 digits" in msg.lower()


def test_return_not_borrowed_by_patron(monkeypatch):
    """
    If there is no active borrow record for (patron_id, book_id), refuse the return.
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, record=None)
    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is False and "no active borrow record" in msg.lower()


def test_return_happy_path_no_late_fee(monkeypatch):
    """
    Happy path (on-time):
    - Record exists
    - Service sets return date and increments availability
    - Message includes success and $0.00 late fee
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, _borrowing_record())
    # Stub fee = 0
    monkeypatch.setattr(
        svc, "calculate_late_fee_for_book",
        lambda *a, **k: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"}
    )
    # DB updates succeed
    monkeypatch.setattr(svc, "update_borrow_record_return_date", lambda *_: True)
    monkeypatch.setattr(svc, "update_book_availability", lambda *_: True)

    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is True
    assert "book returned" in msg.lower()
    assert "$0.00" in msg or "no late fee" in msg.lower()


def test_return_late_fee_tiered(monkeypatch):
    """
    10 days overdue → 7*0.50 + 3*1.00 = $6.50
    (We stub the fee helper to exact numbers; no datetime math.)
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, _borrowing_record())
    monkeypatch.setattr(
        svc, "calculate_late_fee_for_book",
        lambda *a, **k: {"fee_amount": 6.50, "days_overdue": 10, "status": "ok"}
    )
    monkeypatch.setattr(svc, "update_borrow_record_return_date", lambda *_: True)
    monkeypatch.setattr(svc, "update_book_availability", lambda *_: True)

    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is True
    assert "$6.50" in msg or "6.50" in msg
    assert "10" in msg  # days overdue mentioned


def test_return_late_fee_capped(monkeypatch):
    """
    Very late returns cap fee at $15.00.
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, _borrowing_record())
    monkeypatch.setattr(
        svc, "calculate_late_fee_for_book",
        lambda *a, **k: {"fee_amount": 15.00, "days_overdue": 40, "status": "ok"}
    )
    monkeypatch.setattr(svc, "update_borrow_record_return_date", lambda *_: True)
    monkeypatch.setattr(svc, "update_book_availability", lambda *_: True)

    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is True
    assert "$15.00" in msg or "15.00" in msg


def test_return_db_fail_to_set_return_date(monkeypatch):
    """
    If the DB fails to set the return date, surface a DB error and do not change availability.
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, _borrowing_record())
    # Fee stub (not important here)
    monkeypatch.setattr(
        svc, "calculate_late_fee_for_book",
        lambda *a, **k: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"}
    )

    called = {}

    def fail_update_return(*_):
        called["return_attempted"] = True
        return False

    def spy_update_avail(*_):
        called["avail_attempted"] = True
        return True

    monkeypatch.setattr(svc, "update_borrow_record_return_date", fail_update_return)
    monkeypatch.setattr(svc, "update_book_availability", spy_update_avail)

    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is False and "marking return" in msg.lower()
    assert "avail_attempted" not in called  # availability should not be touched if return-date update failed


def test_return_already_returned(monkeypatch):
    """
    If a record already has return_date set, refuse the return (double-return).
    In your implementation, get_borrow_record only returns active rows (return_date IS NULL),
    so an already-returned item appears as 'no active borrow record'.
    """
    _patch_book_exists(monkeypatch)
    _patch_lookup_record(monkeypatch, record=None)  # emulate 'already returned'
    ok, msg = svc.return_book_by_patron("123456", 10)
    assert ok is False and "no active borrow record" in msg.lower()


def test_return_invalid_book_id_type():
    ok, msg = svc.return_book_by_patron("123456", "not-an-int")
    assert ok is False and "invalid book id" in msg.lower()


def test_return_book_not_found(monkeypatch):
    monkeypatch.setattr(svc, "get_book_by_id", lambda bid: None)
    ok, msg = svc.return_book_by_patron("123456", 99)
    assert ok is False and "book not found" in msg.lower()
