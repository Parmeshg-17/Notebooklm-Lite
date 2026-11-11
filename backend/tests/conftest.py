import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client

