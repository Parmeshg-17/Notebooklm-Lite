"""
Test Suite for Multi-Tenant Authorization and Security Isolation in NotebookLM Lite.
Verifies that users cannot access notebooks, documents, or chunks belonging to other tenants.
"""

import uuid
import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.mcp_server.tools import (
    compare_sources_impl,
    get_document_impl,
    get_notebook_sources_impl,
    get_page_content_impl,
    search_documents_impl,
    verify_notebook_access,
)
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User


async def setup_two_tenants():
    """Create two distinct users, each with their own notebook and document."""
    async with async_session_maker() as db:
        # Tenant A
        user_a = User(
            email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="Tenant User A",
        )
        db.add(user_a)
        await db.commit()
        await db.refresh(user_a)

        nb_a = Notebook(title="Notebook A", owner_id=user_a.id)
        db.add(nb_a)
        await db.commit()
        await db.refresh(nb_a)

        doc_a = Document(
            notebook_id=nb_a.id,
            owner_id=user_a.id,
            filename="Document_A.pdf",
            storage_path="doc_a.pdf",
            page_count=5,
            total_chunks=10,
            processing_status="INDEXED",
        )
        db.add(doc_a)
        await db.commit()
        await db.refresh(doc_a)

        # Tenant B
        user_b = User(
            email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="Tenant User B",
        )
        db.add(user_b)
        await db.commit()
        await db.refresh(user_b)

        nb_b = Notebook(title="Notebook B", owner_id=user_b.id)
        db.add(nb_b)
        await db.commit()
        await db.refresh(nb_b)

        doc_b = Document(
            notebook_id=nb_b.id,
            owner_id=user_b.id,
            filename="Document_B.pdf",
            storage_path="doc_b.pdf",
            page_count=5,
            total_chunks=10,
            processing_status="INDEXED",
        )
        db.add(doc_b)
        await db.commit()
        await db.refresh(doc_b)

        return (user_a, nb_a, doc_a), (user_b, nb_b, doc_b)


@pytest.mark.asyncio
async def test_verify_notebook_access_isolation():
    """Verify verify_notebook_access rejects cross-tenant notebook requests."""
    (user_a, nb_a, _), (user_b, nb_b, _) = await setup_two_tenants()

    # User A accessing Notebook A -> True
    assert await verify_notebook_access(nb_a.id, user_a.id) is True

    # User B accessing Notebook B -> True
    assert await verify_notebook_access(nb_b.id, user_b.id) is True

    # User A accessing Notebook B -> False
    assert await verify_notebook_access(nb_b.id, user_a.id) is False

    # User B accessing Notebook A -> False
    assert await verify_notebook_access(nb_a.id, user_b.id) is False


@pytest.mark.asyncio
async def test_search_documents_cross_tenant_denial():
    """Verify search_documents denies access if User A queries User B's notebook."""
    (user_a, nb_a, _), (user_b, nb_b, _) = await setup_two_tenants()

    res = await search_documents_impl(
        notebook_id=str(nb_b.id),
        query="classified findings",
        user_id=str(user_a.id),
    )
    assert "error" in res
    assert "Access denied" in res["error"]
    assert res["results"] == []


@pytest.mark.asyncio
async def test_get_document_cross_tenant_denial():
    """Verify get_document denies access if User A requests User B's document."""
    (user_a, nb_a, _), (user_b, nb_b, doc_b) = await setup_two_tenants()

    res = await get_document_impl(
        document_id=str(doc_b.id),
        notebook_id=str(nb_b.id),
        user_id=str(user_a.id),
    )
    assert "error" in res
    assert "access denied" in res["error"].lower() or "not found" in res["error"].lower()


@pytest.mark.asyncio
async def test_get_page_content_cross_tenant_denial():
    """Verify get_page_content rejects cross-tenant retrieval."""
    (user_a, nb_a, _), (user_b, nb_b, doc_b) = await setup_two_tenants()

    res = await get_page_content_impl(
        document_id=str(doc_b.id),
        page_number=1,
        notebook_id=str(nb_b.id),
        user_id=str(user_a.id),
    )
    assert "error" in res
    assert "access denied" in res["error"].lower()


@pytest.mark.asyncio
async def test_get_notebook_sources_cross_tenant_filtering():
    """Verify get_notebook_sources does not leak documents across tenants."""
    (user_a, nb_a, _), (user_b, nb_b, _) = await setup_two_tenants()

    res = await get_notebook_sources_impl(
        notebook_id=str(nb_a.id),
        user_id=str(user_b.id),
    )
    # Since filter user_id == user_b on nb_a, 0 sources should be returned
    assert res.get("count") == 0
    assert len(res.get("sources", [])) == 0


@pytest.mark.asyncio
async def test_compare_sources_cross_tenant_denial():
    """Verify compare_sources denies access when caller is unauthorized."""
    (user_a, nb_a, _), (user_b, nb_b, _) = await setup_two_tenants()

    res = await compare_sources_impl(
        notebook_id=str(nb_b.id),
        question="What is compared?",
        user_id=str(user_a.id),
    )
    assert "error" in res
    assert "access denied" in res["error"].lower()
