from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        pass
