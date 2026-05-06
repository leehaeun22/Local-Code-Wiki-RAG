from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkResult:
    chunk_type: str
    start_line: int
    end_line: int
    content: str


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, content: str) -> list[ChunkResult]:
        pass
