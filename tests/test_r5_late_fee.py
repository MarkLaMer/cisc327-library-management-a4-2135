'''
author: Mark Nistor
title: R5 — Late Fee Calculation (Service + API)

Covers:
- Service: library_service.calculate_late_fee_for_book(patron_id, book_id)
- API: GET /api/late_fee/<patron_id>/<book_id>

R5 verifies:
- Due = borrow + 14 days; 0.50/day first 7; 1.00/day after; max 15.00
- JSON contains fee_amount and days_overdue

Note: The service currently returns None; behavior tests are xfail until implemented.
'''

import pytest
from datetime import datetime, timedelta
import services.library_service as svc
from services.library_service import calculate_late_fee_for_book


# ---------- helpers ----------
def _freeze_now(monkeypatch, fixed_dt: datetime):
    """Replace library_service.datetime.now() with fixed_dt."""
    class _FixedDT(datetime):
        @classmethod
        def now(cls, *a, **k): return fixed_dt
    monkeypatch.setattr(svc, "datetime", _FixedDT)

def _patch_lookup_borrow(monkeypatch, record):
    """Patch the borrow lookup helper (name to be added later)."""
    monkeypatch.setattr(svc, "get_active_borrow_record", lambda pid, bid: record, raising=False)

def _rec(patron="123456", book=10, borrow=None, due=None):
    borrow = borrow or datetime(2025, 1, 1, 9, 0, 0)
    due = due or (borrow + timedelta(days=14))
    return {"patron_id": patron, "book_id": book, "borrow_date": borrow,
            "due_date": due, "return_date": None, "title": "Any Book"}


# ---------- service tests ----------
# @pytest.mark.xfail(reason="Service returns None until implemented")
def test_current_placeholder_behavior():
    """Document current state: expect a dict once implemented."""
    result = calculate_late_fee_for_book("123456", 10)
    assert isinstance(result, dict)

# @pytest.mark.xfail(reason="Service not implemented yet: on-time → $0.00, 0 days")
def test_late_fee_on_time(monkeypatch):
    rec = _rec()
    _patch_lookup_borrow(monkeypatch, rec)
    _freeze_now(monkeypatch, rec["borrow_date"] + timedelta(days=5))
    out = calculate_late_fee_for_book("123456", 10)
    assert out["fee_amount"] == 0.00 and out["days_overdue"] == 0

# @pytest.mark.xfail(reason="Service not implemented yet: 3 days overdue → $1.50")
def test_late_fee_three_days_overdue(monkeypatch):
    rec = _rec()
    _patch_lookup_borrow(monkeypatch, rec)
    _freeze_now(monkeypatch, rec["due_date"] + timedelta(days=3))
    out = calculate_late_fee_for_book("123456", 10)
    assert out["days_overdue"] == 3 and out["fee_amount"] == 1.50

# @pytest.mark.xfail(reason="Service not implemented yet: 10 days overdue → $6.50")
def test_late_fee_ten_days_overdue(monkeypatch):
    rec = _rec()
    _patch_lookup_borrow(monkeypatch, rec)
    _freeze_now(monkeypatch, rec["due_date"] + timedelta(days=10))
    out = calculate_late_fee_for_book("123456", 10)
    assert out["days_overdue"] == 10 and out["fee_amount"] == 6.50

# @pytest.mark.xfail(reason="Service not implemented yet: cap at $15.00")
def test_late_fee_cap(monkeypatch):
    rec = _rec()
    _patch_lookup_borrow(monkeypatch, rec)
    _freeze_now(monkeypatch, rec["due_date"] + timedelta(days=40))
    out = calculate_late_fee_for_book("123456", 10)
    assert out["fee_amount"] == 15.00


# ---------- API (route) tests ----------
def test_late_fee_api_json(monkeypatch, client):
    """
    Patch the function where the ROUTE calls it: routes.api_routes.calculate_late_fee_for_book.
    Then GET the endpoint and expect JSON.
    """
    import routes.api_routes as api
    monkeypatch.setattr(
        api, "calculate_late_fee_for_book",
        lambda pid, bid: {"fee_amount": 6.50, "days_overdue": 10, "status": "ok"}
    )
    resp = client.get("/api/late_fee/123456/10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["fee_amount"] == 6.50 and data["days_overdue"] == 10

def test_late_fee_api_not_implemented_returns_501(monkeypatch, client):
    """If the service returns a 'not implemented' status, route should return 501."""
    import routes.api_routes as api
    monkeypatch.setattr(
        api, "calculate_late_fee_for_book",
        lambda pid, bid: {"fee_amount": 0.0, "days_overdue": 0, "status": "not implemented"}
    )
    resp = client.get("/api/late_fee/123456/10")
    assert resp.status_code == 501


# Additional tests - A2
def test_ten_days_overdue_tiered():
    """10 days overdue → fee = 7*0.50 + 3*1.00 = $6.50; JSON has fee_amount & days_overdue."""
    from datetime import datetime, timedelta
    due = datetime(2025, 1, 10, 12, 0, 0)
    now = due + timedelta(days=10)
    out = calculate_late_fee_for_book("123456", 10, {"due_date": due.isoformat()}, now)
    assert out["days_overdue"] == 10 and out["fee_amount"] == 6.50

def test_fee_cap_at_15():
    """Very late returns are capped at $15.00 (e.g., 40 days overdue)."""
    from datetime import datetime, timedelta
    due = datetime(2025, 1, 10, 12, 0, 0)
    now = due + timedelta(days=40)
    out = calculate_late_fee_for_book("123456", 10, {"due_date": due.isoformat()}, now)
    assert out["fee_amount"] == 15.00

