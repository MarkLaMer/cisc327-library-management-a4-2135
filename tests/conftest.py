import sys
from pathlib import Path
import pytest

# Add project root (parent of /tests) to Python path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture
def client():
    """
    Returns a Flask test client regardless of whether you use an app factory
    or a module-level `app`.
    """
    try:
        # Preferred: application factory
        from app import create_app
        app = create_app()
    except Exception:
        # Fallback: module-level app = Flask(__name__)
        from app import app as _app
        app = _app

    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c