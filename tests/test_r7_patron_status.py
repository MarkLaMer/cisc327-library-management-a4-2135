'''
author: Mark Nistor
title: R7 — Patron Status Report (Business-Logic Tests)

These tests cover:
- Service: library_service.get_patron_status_report(patron_id)

R7 verifies the report includes:
- Currently borrowed books with due dates
- Total late fees owed
- Number of books currently borrowed
- Borrowing history
'''

import pytest
from datetime import datetime, timedelta

from library_service import get_patron_status_report


def _key(d, *candidates):
    """Return the first existing key from candidates (compat with older/newer shapes)."""
    for k in candidates:
        if k in d:
            return d[k]
    return None


def _freeze_now(monkeypatch, fixed_dt: datetime):
    """Freeze library_service.datetime.now() for reproducible fee calculations."""
    import library_service as svc
    class _FixedDT(datetime):
        @classmethod
        def now(cls, *a, **k):
            return fixed_dt
    monkeypatch.setattr(svc, "datetime", _FixedDT)


def _active(bid, title, days_until_due):
    now = datetime(2025, 1, 10, 12, 0, 0)
    borrow = now - timedelta(days=14 - days_until_due)
    return {
        "book_id": bid,
        "title": title,
        "borrow_date": borrow,
        "due_date": borrow + timedelta(days=14),
        "return_date": None,
    }


def _history_entry(bid, title, overdue_days=0):
    borrow = datetime(2024, 12, 1, 10, 0, 0)
    due = borrow + timedelta(days=14)
    ret = due + timedelta(days=overdue_days)
    return {
        "book_id": bid,
        "title": title,
        "borrow_date": borrow,
        "due_date": due,
        "return_date": ret,
    }


def test_current_placeholder_is_dict():
    """Current placeholder returns {} — keep this sanity test for now."""
    out = get_patron_status_report("123456")
    assert isinstance(out, dict)


def test_status_includes_current_loans_and_count(monkeypatch):
    import library_service as svc
    active = [
        _active(10, "Clean Code", days_until_due=3),
        _active(11, "Fluent Python", days_until_due=1),
    ]
    # stubs: active loans + no history yet
    monkeypatch.setattr(svc, "get_active_borrows_by_patron", lambda pid: active, raising=False)
    monkeypatch.setattr(svc, "get_borrow_history_by_patron", lambda pid: [], raising=False)
    # no fees (on time) — accept optional kwargs from service
    monkeypatch.setattr(
        svc,
        "calculate_late_fee_for_book",
        lambda pid, bid, **kw: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"},
        raising=False,
    )

    out = get_patron_status_report("123456")
    loans = _key(out, "current_loans", "currently_borrowed") or []
    count = _key(out, "current_count", "current_borrow_count") or 0

    # Require at least our two stubbed loans, without asserting specific IDs (DB may seed extras)
    assert len(loans) >= 2
    assert count >= 2
    # Spot-check required fields exist on each loan
    for e in loans:
        assert {"book_id", "title", "due_date"} <= set(e.keys())


def test_status_totals_late_fees(monkeypatch):
    import library_service as svc
    active = [
        _active(10, "One", days_until_due=-2),  # overdue 2d
        _active(11, "Two", days_until_due=-10), # overdue 10d → 6.50 fee
    ]
    monkeypatch.setattr(svc, "get_active_borrows_by_patron", lambda pid: active, raising=False)
    monkeypatch.setattr(svc, "get_borrow_history_by_patron", lambda pid: [], raising=False)

    def _fee(pid, bid, **kw):
        return {
            "fee_amount": 1.0 if bid == 10 else 6.5,
            "days_overdue": 2 if bid == 10 else 10,
            "status": "ok",
        }
    monkeypatch.setattr(svc, "calculate_late_fee_for_book", _fee, raising=False)

    out = get_patron_status_report("123456")
    total = _key(out, "total_late_fees", "total_late_fees_owed") or 0.0
    assert abs(total - 7.5) < 1e-9


# def test_status_includes_history(monkeypatch):
#     import library_service as svc
#     hist = [
#         _history_entry(3, "Pragmatic Programmer", overdue_days=0),
#         _history_entry(4, "Refactoring", overdue_days=5),
#     ]
#     monkeypatch.setattr(svc, "get_active_borrows_by_patron", lambda pid: [], raising=False)
#     monkeypatch.setattr(svc, "get_borrow_history_by_patron", lambda pid: hist, raising=False)
#     monkeypatch.setattr(
#         svc,
#         "calculate_late_fee_for_book",
#         lambda pid, bid, **kw: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"},
#         raising=False,
#     )

#     out = get_patron_status_report("123456")
#     history = _key(out, "history", "history") or []

#     # Require at least our two entries; don’t match exact titles since DB may add more
#     assert len(history) >= 2
#     for h in history[:2]:  # spot-check a couple
#         assert {"book_id", "title", "borrow_date", "due_date", "return_date"} <= set(h.keys())


def test_status_shape_keys(monkeypatch):
    """
    Expected structure (example):
      {
        "current_loans": [ {book_id,title,due_date,...}, ... ],
        "current_count": int,
        "total_late_fees": float,
        "history": [ ... ]
      }
    """
    import library_service as svc
    monkeypatch.setattr(svc, "get_active_borrows_by_patron", lambda pid: [], raising=False)
    monkeypatch.setattr(svc, "get_borrow_history_by_patron", lambda pid: [], raising=False)
    monkeypatch.setattr(
        svc,
        "calculate_late_fee_for_book",
        lambda pid, bid, **kw: {"fee_amount": 0.0, "days_overdue": 0, "status": "ok"},
        raising=False,
    )

    out = get_patron_status_report("123456")
    for key in ("current_loans", "current_count", "total_late_fees", "history"):
        assert key in out
