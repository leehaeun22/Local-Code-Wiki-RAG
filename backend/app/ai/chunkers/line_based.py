from app.ai.chunkers.base import BaseChunker, ChunkResult


class LineBasedChunker(BaseChunker):
    def __init__(self, chunk_size: int = 120, overlap: int = 20) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, content: str) -> list[ChunkResult]:
        lines = content.splitlines(keepends=True)

        if not lines:
            return [ChunkResult(chunk_type="line", start_line=1, end_line=1, content="")]

        if len(lines) <= self.chunk_size:
            return [
                ChunkResult(
                    chunk_type="line",
                    start_line=1,
                    end_line=len(lines),
                    content="".join(lines),
                ),
            ]

        chunks: list[ChunkResult] = []
        step = self.chunk_size - self.overlap
        start = 0

        while start < len(lines):
            end = min(start + self.chunk_size, len(lines))
            chunks.append(
                ChunkResult(
                    chunk_type="line",
                    start_line=start + 1,
                    end_line=end,
                    content="".join(lines[start:end]),
                ),
            )

            if end == len(lines):
                break

            start += step

        return chunks
