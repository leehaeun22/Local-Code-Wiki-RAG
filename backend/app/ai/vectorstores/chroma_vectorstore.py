from typing import Any

from app.ai.vectorstores.base_vectorstore import VectorStore
from app.core.config import settings


class ChromaVectorStore(VectorStore):
    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        import chromadb

        self.client = chromadb.HttpClient(
            host=host or settings.chroma_host,
            port=port or settings.chroma_port,
        )

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection = self.client.get_or_create_collection(name=collection_name)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        collection = self.client.get_or_create_collection(name=collection_name)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        return [
            {
                "id": ids[index],
                "document": documents[index],
                "metadata": metadatas[index],
                "distance": distances[index],
            }
            for index in range(len(ids))
        ]
