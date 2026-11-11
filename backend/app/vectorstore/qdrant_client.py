import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient, models
from app.core.config import settings
from app.vectorstore.embeddings import VECTOR_DIMENSION

logger = logging.getLogger("app.vectorstore.qdrant")


class QdrantService:
    def __init__(self):
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            q_url = (settings.QDRANT_URL or "").strip()
            q_key = (settings.QDRANT_API_KEY or "").strip() or None
            if q_url == ":memory:":
                logger.info("Initializing in-memory Qdrant client")
                self._client = QdrantClient(":memory:")
            else:
                logger.info(f"Connecting to Qdrant at {q_url}")
                self._client = QdrantClient(
                    url=q_url,
                    api_key=q_key,
                )
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        """Create Qdrant collection if it does not exist and ensure required payload indexes."""
        try:
            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=VECTOR_DIMENSION,
                        distance=models.Distance.COSINE,
                    ),
                )
            # Create payload indices for fields used in query filters
            for field in ["owner_id", "notebook_id", "document_id", "filename"]:
                try:
                    self._client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    async def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]],
    ) -> None:
        """Store chunk vectors and payloads in Qdrant."""
        if not chunks or not vectors:
            return

        points: List[models.PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["chunk_id"]))
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=chunk,
                )
            )

        batch_size = 250
        for i in range(0, len(points), batch_size):
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
            )
        logger.info(f"Upserted {len(points)} chunks into Qdrant collection {self.collection_name}")

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        """Delete all chunks belonging to a document."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted vector chunks for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")

    async def count_document_chunks(self, document_id: uuid.UUID) -> int:
        """Count stored points for a document in Qdrant."""
        try:
            res = await asyncio.to_thread(
                self.client.count,
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                ),
                exact=True,
            )
            return res.count
        except Exception as e:
            logger.warning(f"Error counting chunks for document {document_id}: {e}")
            return 0

    async def fetch_notebook_chunks(
        self,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 2500,
    ) -> List[Dict[str, Any]]:
        """Fetch all chunks for a notebook to power lexical BM25 indexing."""
        must_conditions: List[models.Condition] = [
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(user_id)),
            ),
            models.FieldCondition(
                key="notebook_id",
                match=models.MatchValue(value=str(notebook_id)),
            ),
        ]
        if document_ids:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=[str(d) for d in document_ids]),
                )
            )

        scroll_filter = models.Filter(must=must_conditions)
        try:
            points, _ = await asyncio.to_thread(
                self.client.scroll,
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            results: List[Dict[str, Any]] = []
            for p in points:
                payload = p.payload or {}
                results.append({
                    "chunk_id": payload.get("chunk_id") or str(p.id),
                    "document_id": payload.get("document_id"),
                    "notebook_id": payload.get("notebook_id"),
                    "filename": payload.get("filename", ""),
                    "page_number": payload.get("page_number", 1),
                    "chunk_index": payload.get("chunk_index", 0),
                    "text": payload.get("text", ""),
                })
            return results
        except Exception as e:
            logger.warning(f"Error fetching notebook chunks for BM25: {e}")
            return []

    async def search(
        self,
        query_vector: List[float],
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Similarity search with strict user and notebook isolation.
        User A cannot retrieve User B's chunks under any circumstances.
        """
        # Strict security filter: user_id AND notebook_id
        must_conditions: List[models.Condition] = [
            models.FieldCondition(
                key="owner_id",
                match=models.MatchValue(value=str(user_id)),
            ),
            models.FieldCondition(
                key="notebook_id",
                match=models.MatchValue(value=str(notebook_id)),
            ),
        ]

        if document_ids:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=[str(d) for d in document_ids]),
                )
            )

        query_filter = models.Filter(must=must_conditions)

        # Execute search
        response = await asyncio.to_thread(
            self.client.query_points,
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        results: List[Dict[str, Any]] = []
        for hit in response.points:
            payload = hit.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id"),
                "document_id": payload.get("document_id"),
                "notebook_id": payload.get("notebook_id"),
                "filename": payload.get("filename", ""),
                "page_number": payload.get("page_number", 1),
                "chunk_index": payload.get("chunk_index", 0),
                "text": payload.get("text", ""),
                "score": hit.score,
            })

        return results


qdrant_service = QdrantService()

