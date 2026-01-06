"""Unit tests for text chunking service"""

import pytest

from app.services.rag.chunking import ChunkingService


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

    def test_long_text_with_sentence_boundaries(self):
        """Test chunking of long text with sentence boundaries - regression test for infinite loop bug"""
        service = ChunkingService(chunk_size=400, overlap=80)

        # Create a realistic long text with sentences (simulate academic paper)
        sentences = [
            "This is the first sentence of a research paper.",
            "It discusses various important topics in the field.",
            "The methodology section describes the experimental setup.",
            "Results were analyzed using statistical methods.",
            "Discussion of findings reveals interesting patterns.",
        ]
        # Repeat to create a text long enough to trigger the bug
        text = " ".join(
            sentences * 50
        )  # ~250 chars per repetition * 50 = ~12,500 chars

        chunks = service.split_text(text, split_by_sentence=True, preserve_words=True)

        # Should create many chunks, not just 1-2
        expected_min_chunks = len(text) // (service.chunk_size - service.overlap) // 2
        assert (
            len(chunks) >= expected_min_chunks
        ), f"Expected at least {expected_min_chunks} chunks, got {len(chunks)}"

        # All chunks should have reasonable size
        for i, chunk in enumerate(
            chunks[:-1]
        ):  # Exclude last chunk which might be shorter
            assert (
                len(chunk) > 100
            ), f"Chunk {i} is too short ({len(chunk)} chars): likely infinite loop bug"

        # Verify overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            # The end of one chunk should overlap with the start of the next
            overlap_text = chunks[i][-service.overlap :]
            next_start = chunks[i + 1][: service.overlap]
            # They should have some overlap (might not be exact due to sentence boundaries)
            assert (
                len(set(overlap_text.split()) & set(next_start.split())) > 0
            ), f"No overlap found between chunk {i} and {i+1}"

    def test_sparse_sentence_boundaries_bug(self):
        """Regression test for bug where sparse sentence endings cause infinite loop

        The bug occurs when:
        1. First chunk finds a sentence ending near position 369 (within 400 char chunk)
        2. Second chunk starts at 289 (369 - 80 overlap)
        3. Second chunk (289-689) finds the SAME sentence ending at absolute position 369
        4. This causes next_start to equal current start (289 == 289), triggering break
        """
        service = ChunkingService(chunk_size=400, overlap=80)

        # Simulate academic paper header with sparse sentence endings
        # First sentence ending should be around position 369
        text = (
            "Impact of customer focus on technology\n"
            "leadership via technology development\n"
            "capability –a moderated mediation model\n"
            "Zafar Husain\n"
            "College of Business, Al Ain University, United Arab Emirates\n"
            "Mumin Dayan\n"
            "United Arab Emirates University, Al Ain, United Arab Emirates\n"
            "Sushil\n"
            "Department of Management Studies, Indian Institute of Technology Delhi, New Delhi, India, and\n"
            "C. Anthony Di Benedetto\n"
            # Continue with more text to create a large document
            "Marketing and Supply Chain Management, Temple University, Philadelphia, Pennsylvania, USA\n"
            "Abstract\n"
            "Purpose. This study aims to develop and empirically examine a model.\n"
        ) * 200  # Create a 60KB+ document

        chunks = service.split_text(text, split_by_sentence=True, preserve_words=True)

        # Should create approximately (len(text) / (chunk_size - overlap)) chunks
        expected_chunks = len(text) // (service.chunk_size - service.overlap)
        assert (
            len(chunks) > 10
        ), f"Only got {len(chunks)} chunks for {len(text)} chars - infinite loop bug detected"
        assert (
            len(chunks) >= expected_chunks * 0.5
        ), f"Expected ~{expected_chunks} chunks, got {len(chunks)} - chunking is broken"
