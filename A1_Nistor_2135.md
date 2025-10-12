Name: Mark Nistor
ID: 20412135
Group: 3

# Test Breakdown

| Function name         | Implementation status | What is missing (if any)                                                                                                                                |
|-----------------------|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| add_book_to_catalog   | Partial               | Enforce ISBN to be **13 digits** (digits-only). Current code only checks `len(isbn) == 13`. All other validations in R1 pass (see test breakdown below). |
| Catalog display — `/catalog`  | Complete              | N/A |
| borrow_book_by_patron   | Partial               | Borrowing limit should block at **5** (use `>= 5`). Current code uses `> 5`, allowing an at-limit checkout.  |
| return_book_by_patron | Partial               | Implement full return flow: validate 6-digit patron ID; verify patron borrowed this book; prevent double-return; set `return_date`; increment availability (+1); compute/display late fee (R5 rules: 14-day due, $0.50/day first 7, $1/day after, cap $15); handle DB failures cleanly. |
| calculate_late_fee_for_book                       | Partial               | Implement 14-day due; fees: $0.50/day first 7, then $1/day; **cap $15**; return dict with `fee_amount` and `days_overdue` (service returns None now). |
| search_books_in_catalog   | Partial               | Implement actual search: partial **case-insensitive** match for **title** and **author**; **exact** match for **ISBN**. Current placeholder returns [] which happens to satisfy “partial ISBN should not match” and “unknown type returns []”. |
| get_patron_status_report   | Partial               | Build full report: list **current_loans** with **due_date**, compute **current_count**, sum **total_late_fees** (via R5), include **history**, and return a stable structure with keys: `current_loans`, `current_count`, `total_late_fees`, `history`. |



## R1 — Add Book To Catalog
`pytest -q -vv tests/test_r1_add_book.py`

| Test case                                 | Result  |
|-------------------------------------------|---------|
| test_add_book_valid_input                 | PASSED  |
| test_add_book_invalid_isbn_too_short      | PASSED  |
| test_add_book_missing_title               | PASSED  |
| test_add_book_invalid_total_copies        | PASSED  |
| test_add_book_author_too_long             | PASSED  |
| test_add_book_duplicate_isbn              | PASSED  |
| test_add_book_author_required             | PASSED  |
| test_add_book_title_too_long              | PASSED  |
| test_add_book_isbn_too_long               | PASSED  |
| test_add_book_total_copies_zero           | PASSED  |
| test_add_book_isbn_not_all_digits         | XFAIL (Spec says ‘13 digits’; implementation checks length only) |


## R2 — Catalog Display (route/UI)
`pytest -q -vv tests/test_r2_catalog_display.py`

| Test case                                      | Result |
|-----------------------------------------------|--------|
| test_catalog_headers_and_rows                 | PASSED |
| test_borrow_form_present_for_available_book   | PASSED |
| test_no_borrow_form_when_unavailable          | PASSED |
| test_empty_state                               | PASSED |

## R3 — Borrowing (business logic)  ← has xfail expectations
`pytest -q -rxX tests/test_r3_borrow.py`

| Test case                                           | Result |
|-----------------------------------------------------|--------|
| test_borrow_happy_path                              | PASSED |
| test_borrow_invalid_patron_id[]                     | PASSED |
| test_borrow_invalid_patron_id[12345]                | PASSED |
| test_borrow_invalid_patron_id[abcdef]               | PASSED |
| test_borrow_invalid_patron_id[12345a]               | PASSED |
| test_borrow_invalid_patron_id[ 123456]              | PASSED |
| test_borrow_invalid_patron_id[1234567]              | PASSED |
| test_borrow_book_not_found                          | PASSED |
| test_borrow_book_unavailable                        | PASSED |
| test_borrow_limit_reached_at_5_should_fail          | XFAIL  *(Spec: max 5; implementation only blocks when count > 5)* |
| test_borrow_limit_over_5_fails                      | PASSED |
| test_borrow_db_insert_failure                       | PASSED |
| test_borrow_db_update_availability_failure          | PASSED |

## R4 — Return Processing (business logic)  ← has xfail expectations
`pytest -q -rxX -vv tests/test_r4_return.py`

| Test case                                   | Result |
|---------------------------------------------|--------|
| test_current_status_not_implemented         | PASSED |
| test_return_invalid_patron_id[]             | XFAIL *(should validate patron ID is 6 digits)* |
| test_return_invalid_patron_id[12345]        | XFAIL |
| test_return_invalid_patron_id[abcdef]       | XFAIL |
| test_return_invalid_patron_id[12345a]       | XFAIL |
| test_return_invalid_patron_id[ 123456]      | XFAIL |
| test_return_invalid_patron_id[1234567]      | XFAIL |
| test_return_not_borrowed_by_patron          | XFAIL *(should verify active borrow record)* |
| test_return_happy_path_no_late_fee          | XFAIL *(should set return date & increment availability)* |
| test_return_late_fee_tiered                 | XFAIL *(should compute tiered late fees)* |
| test_return_late_fee_capped                 | XFAIL *(should cap fee at $15.00)* |
| test_return_db_fail_to_set_return_date      | XFAIL *(must handle DB failure cleanly)* |
| test_return_already_returned                | XFAIL *(must prevent double-returns)* |

## R5 — Late Fee (service + API)  ← has xfail expectations
`pytest -q -rxX -vv tests/test_r5_late_fee.py`

| Test case                                      | Result | Notes |
|-----------------------------------------------|--------|-------|
| test_current_placeholder_behavior             | XFAIL  | Service returns None until implemented |
| test_late_fee_on_time                         | XFAIL  | On-time → $0.00, 0 days |
| test_late_fee_three_days_overdue              | XFAIL  | 3 days overdue → $1.50 |
| test_late_fee_ten_days_overdue                | XFAIL  | 10 days overdue → $6.50 |
| test_late_fee_cap                             | XFAIL  | Cap at $15.00 |
| test_late_fee_api_json                        | PASSED | Route returns JSON with `fee_amount` and `days_overdue` when service returns data |
| test_late_fee_api_not_implemented_returns_501 | PASSED | Route returns 501 when service status is “not implemented” |

## R6 — Search (business logic)  ← has xfail expectations
`pytest -q -rxX -vv tests/test_r6_search.py`

| Test case                                   | Result | Notes |
|---------------------------------------------|--------|-------|
| test_current_placeholder_returns_list       | PASSED | Returns a list (placeholder sanity) |
| test_search_title_partial_case_insensitive  | XFAIL  | Should match partial, case-insensitive title |
| test_search_author_partial_case_insensitive | XFAIL  | Should match partial, case-insensitive author |
| test_search_isbn_exact                      | XFAIL  | Should match only exact ISBN |
| test_search_isbn_partial_no_match           | XPASS  | Placeholder returned [], which matches expectation (no partial ISBN match) |
| test_search_unknown_type_returns_empty      | XPASS  | Placeholder returned [] for unknown type (acceptable default) |

## R7 — Patron Status Report (business logic)  ← has xfail expectations
`pytest -q -rxX -vv tests/test_r7_patron_status.py`

| Test case                                          | Result | Notes                                                                                             |
| -------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------- |
| test_current_placeholder_is_dict               | PASSED | Placeholder returns a dict (sanity check).                                                        |
| test_status_includes_current_loans_and_count | XFAIL  | Should aggregate current loans, counts, and fees.                                                 |
| test_status_totals_late_fees                   | XFAIL  | Should sum late fees across active overdues.                                                      |
| test_status_includes_history                    | XFAIL  | Should include past returns in the history section.                                               |
| test_status_shape_keys                          | XFAIL  | Structure keys should be stable (`current_loans`, `current_count`, `total_late_fees`, `history`). |
