"""
Test Suite for FastAPI Chat API Endpoints Integration and Contracts.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import async_session_maker
from app.main import app
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User


async def get_test_user_and_notebook():
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if nb:
            user_res = await db.execute(select(User).where(User.id == nb.owner_id))
            user = user_res.scalar_one_or_none()
            return user, nb

        # Fallback
        user = User(
            email=f"api_test_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="API Tester",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        nb = Notebook(title="API Test Notebook", owner_id=user.id)
        db.add(nb)
        await db.commit()
        await db.refresh(nb)
        return user, nb


@pytest.mark.asyncio
async def test_chat_endpoint_contract():
    """Verify POST /api/v1/notebooks/{id}/chat returns expected schema with citations and tools."""
    user, nb = await get_test_user_and_notebook()
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "question": "What is AI engineering?",
            "filter_sources": True,
        }
        res = await ac.post(
            f"/api/v1/notebooks/{nb.id}/chat",
            json=payload,
            headers=headers,
        )

        assert res.status_code == 200
        data = res.json()

        # Contract assertion
        assert "id" in data
        assert "answer" in data
        assert "content" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert "grounded" in data
        assert "insufficient_evidence" in data
        assert "intent" in data
        assert "tools_used" in data
        assert isinstance(data["tools_used"], list)

        # Check citation structure if citations are present
        if data["citations"]:
            cit = data["citations"][0]
            assert "documentId" in cit or "document_id" in cit
            assert "pageNumber" in cit or "page_number" in cit
            assert "excerpt" in cit
            assert "relevanceScore" in cit


@pytest.mark.asyncio
async def test_chat_history_endpoint():
    """Verify GET /api/v1/notebooks/{id}/chat/history returns message history."""
    user, nb = await get_test_user_and_notebook()
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/notebooks/{nb.id}/chat/history",
            headers=headers,
        )
        assert res.status_code == 200
        history = res.json()
        assert isinstance(history, list)


@pytest.mark.asyncio
async def test_chat_feedback_endpoint():
    """Verify POST /api/v1/notebooks/{id}/chat/feedback stores user feedback."""
    user, nb = await get_test_user_and_notebook()
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        feedback_payload = {
            "message_id": str(uuid.uuid4()),
            "feedback": "positive",
            "notes": "Clear citation to page 14",
        }
        res = await ac.post(
            f"/api/v1/notebooks/{nb.id}/chat/feedback",
            json=feedback_payload,
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json().get("status") == "success"


@pytest.mark.asyncio
async def test_chat_unauthorized_user():
    """Verify accessing another user's notebook chat returns 403 Forbidden."""
    user, nb = await get_test_user_and_notebook()

    # Create distinct other user in database
    async with async_session_maker() as db:
        other_user = User(
            email=f"other_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="Other User",
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

    token = create_access_token(subject=other_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/notebooks/{nb.id}/chat",
            json={"question": "Test unauthorized"},
            headers=headers,
        )
        assert res.status_code in [403, 404]
