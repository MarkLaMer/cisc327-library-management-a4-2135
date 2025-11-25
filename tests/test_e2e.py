# tests/test_e2e.py

import os
import signal
import subprocess
import time
import requests
import sys
import platform

import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://127.0.0.1:5000"

# Check if we're on CI - if so, go headless; otherwise keep the browser visible for local debugging
if os.getenv("CI", "").lower() == "true" or os.getenv("GITHUB_ACTIONS", "").lower() == "true":
    use_headless = True
else:
    use_headless = False  # show the browser window locally so you can see what's happening

# ---------- Fixtures ----------
def wait_for_server(url, timeout=10):
    time.sleep(timeout)

SKIP_E2E_ON_MAC_CI = (
    platform.system() == "Darwin"
    and os.getenv("CI", "").lower() == "true"
)

@pytest.fixture(scope="session")
def flask_server():
    env = os.environ.copy()
    env["FLASK_ENV"] = "testing"

    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        env=env,
    )

    try:
        wait_for_server(BASE_URL, timeout=10)
    except Exception:
        if proc.poll() is None:
            if os.name == "nt":
                proc.terminate()
            else:
                os.kill(proc.pid, signal.SIGTERM)
        raise

    yield

    if proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.kill(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()



@pytest.fixture
def page(flask_server):
    """
    Launch a Chromium browser for each test.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=use_headless)  # flip to False if you wanna debug
        page = browser.new_page()
        yield page
        browser.close()

# ---------- Helper ----------

def add_test_book(page, title, author, isbn=None, total_copies="3"):
    """
    Quick helper function to add a book through the UI.
    """
    page.goto(f"{BASE_URL}/add_book")

    # no ISBN? no problem - just cook up a random one to avoid collisions
    if isbn is None:
        timestamp = int(time.time() * 1000) % 1000000000000  # grab 12 digits from the timestamp
        check_digit = (abs(hash(title)) % 9) + 1          # add a random 13th digit (1-9)
        isbn = f"{timestamp:012d}{check_digit}"

    page.fill('input[name="title"]', title)
    page.fill('input[name="author"]', author)
    page.fill('input[name="isbn"]', isbn)
    page.fill('input[name="total_copies"]', str(total_copies))

    page.click('button[type="submit"]')
    # give it a sec for the page to redirect and re-render
    page.wait_for_timeout(300)


# ---------- Test 1: Add + Borrow flow ----------
@pytest.mark.skipif(SKIP_E2E_ON_MAC_CI, reason="Skip Playwright E2E on macOS CI")
def test_add_and_borrow_book_flow(page):
    """
    Full flow test:
    1. Add a new book to the catalog (fill title, author, ISBN, copies)
    2. Verify the book appears in the catalog
    3. Navigate to borrow book page
    4. Borrow the book using a patron ID
    5. Verify the borrow confirmation message appears
    """
    book_title = "Dracula"
    book_author = "Bram Stoker"
    patron_num = "654321"

    # Step 1: add the book to the catalog
    add_test_book(page, book_title, book_author)

    # Step 2: verify it actually showed up
    page.goto(f"{BASE_URL}/catalog")
    # wait for the page to load properly
    expect(page.locator("h2")).to_contain_text("Book Catalog")
    expect(page.locator("table")).to_be_visible()

    # make sure our new book is in there
    expect(page.locator("body")).to_contain_text(book_title)

    # Step 3 & 4: borrow it straight from the catalog - just fill in patron ID and hit borrow
    # (books are sorted alphabetically, so our new one should be easy to find)
    patron_field = page.locator("tbody input[name='patron_id']").first
    expect(patron_field).to_be_visible()
    patron_field.fill(patron_num)
    # click the borrow button next to the input
    patron_field.locator("xpath=ancestor::form[1]//button[contains(., 'Borrow')]").click()

    # Step 5: confirm we get the success message
    page_body = page.locator("body")
    expect(page_body).to_contain_text("Successfully borrowed")
    expect(page_body).to_contain_text(book_title)


# ---------- Test 2: Search flow (example) ----------
@pytest.mark.skipif(SKIP_E2E_ON_MAC_CI, reason="Skip Playwright E2E on macOS CI")
def test_search_catalog_flow(page):
    """
    Another realistic scenario:
      1. Add a book
      2. Head to the search page
      3. Search by title
      4. Verify the search actually finds it
    """

    book_title = "Searchable E2E Book"
    book_author = "Search Author"

    # add the book (use a fixed ISBN so we don't get weird collisions)
    add_test_book(page, book_title, book_author, isbn="9780000000001")

    # Step 2: navigate to search
    page.goto(f"{BASE_URL}/search")

    # Step 3: search for our book by title
    page.fill('input[name="q"]', book_title)
    page.click('button[type="submit"]')

    # Step 4: make sure the results show up
    expect(page.locator("body")).to_contain_text(book_title)
    expect(page.locator("body")).to_contain_text(book_author)
