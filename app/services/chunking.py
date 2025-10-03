"""Text chunking service for splitting documents into smaller pieces"""

import re


class ChunkingService:
    """Service for splitting text into chunks with overlap"""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize chunking service

        Args:
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of overlapping characters between chunks

        Raises:
            ValueError: If overlap >= chunk_size
        """
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(
        self,
        text: str,
        split_by_sentence: bool = False,
        preserve_words: bool = False,
    ) -> list[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Input text to split
            split_by_sentence: Try to split at sentence boundaries
            preserve_words: Avoid splitting words in the middle

        Returns:
            List of text chunks
        """
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Adjust end position based on options
            if end < len(text):
                if split_by_sentence:
                    end = self._adjust_to_sentence_boundary(text, start, end)
                elif preserve_words:
                    end = self._adjust_to_word_boundary(text, start, end)

            chunk = text[start:end]
            chunks.append(chunk)

            # Move start position with overlap
            if end >= len(text):
                break

            # Calculate next start with overlap
            next_start = end - self.overlap
            if next_start <= start:
                break  # Prevent infinite loop
            start = next_start

        return chunks

    def _adjust_to_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Adjust end position to nearest sentence boundary

        Args:
            text: Full text
            start: Start position in text (absolute)
            end: End position in text (absolute)

        Returns:
            Adjusted end position (absolute) at a sentence boundary
        """
        # Look for sentence endings (. ! ?) within the chunk
        chunk = text[start:end]
        # Match sentence endings followed by space, newline, or end of text
        sentence_endings = [m.end() for m in re.finditer(r"[.!?](?:\s|$)", chunk)]

        if sentence_endings:
            # Convert relative positions to absolute positions
            absolute_endings = [start + pos for pos in sentence_endings]

            # Filter out sentence endings that are too close to the start
            # (within overlap distance) to avoid reusing the same sentence ending
            min_distance = self.overlap if hasattr(self, 'overlap') else 0
            valid_endings = [pos for pos in absolute_endings if pos > start + min_distance]

            if valid_endings:
                # Use the last valid sentence ending
                return valid_endings[-1]

        # If no valid sentence ending found, use original end (don't adjust)
        return end

    def _adjust_to_word_boundary(self, text: str, start: int, end: int) -> int:
        """Adjust end position to nearest word boundary"""
        # Look backward for a space
        while end > start and not text[end - 1].isspace():
            end -= 1

        # If we went too far back, just use the original end
        if end - start < self.chunk_size * 0.5:
            end = min(start + self.chunk_size, len(text))

        return end
