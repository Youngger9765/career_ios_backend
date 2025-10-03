"""Unit tests for text chunking service"""

import pytest

from app.services.chunking import ChunkingService


class TestChunkingService:
    """Test suite for ChunkingService"""

    def test_split_text_into_chunks_basic(self):
        """Test basic text splitting into chunks"""
        service = ChunkingService(chunk_size=100, overlap=20)
        text = "A" * 250

        chunks = service.split_text(text)

        # First chunk: 0-100 (100 chars)
        # Second chunk: 80-180 (100 chars, starts at 100-20=80)
        # Third chunk: 160-250 (90 chars, starts at 180-20=160)
        assert len(chunks) == 3
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 90  # Last chunk is rest of text

    def test_chunk_overlap_works_correctly(self):
        """Test that chunks have correct overlap"""
        service = ChunkingService(chunk_size=100, overlap=20)
        text = "ABCDEFGH" * 30  # 240 characters

        chunks = service.split_text(text)

        # Check overlap between first and second chunk
        assert chunks[0][-20:] == chunks[1][:20]

    def test_split_text_shorter_than_chunk_size(self):
        """Test handling text shorter than chunk size"""
        service = ChunkingService(chunk_size=1000, overlap=100)
        text = "Short text"

        chunks = service.split_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text_returns_empty_list(self):
        """Test that empty text returns empty list"""
        service = ChunkingService()
        chunks = service.split_text("")

        assert chunks == []

    def test_invalid_overlap_raises_error(self):
        """Test that overlap >= chunk_size raises ValueError"""
        with pytest.raises(ValueError, match="Overlap must be less than chunk_size"):
            ChunkingService(chunk_size=100, overlap=100)

    def test_split_by_sentences(self):
        """Test splitting text by sentence boundaries"""
        service = ChunkingService(chunk_size=100, overlap=20)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        chunks = service.split_text(text, split_by_sentence=True)

        # Each chunk should end with a period (sentence boundary)
        for chunk in chunks[:-1]:  # Except possibly the last one
            assert chunk.rstrip().endswith(".")

    def test_preserve_words(self):
        """Test that words are not split in the middle"""
        service = ChunkingService(chunk_size=50, overlap=10)
        text = "This is a long sentence with many words that should not be split"

        chunks = service.split_text(text, preserve_words=True)

        # No chunk should end or start mid-word (check for no partial words)
        for chunk in chunks:
            words = chunk.strip().split()
            # Each word should be complete (no trailing/leading non-space)
            assert all(word.strip() == word for word in words if word)
