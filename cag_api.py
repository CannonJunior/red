"""
CAG (Cache-Augmented Generation) API Module

This module provides zero-cost, in-memory context caching for LLM interactions.
Unlike RAG which retrieves relevant chunks, CAG preloads entire documents into
the model's context window for zero-latency responses.

Architecture:
- In-memory document storage with token counting
- Context window management (~128K tokens for modern LLMs)
- Direct context injection into LLM prompts
- No vector database or retrieval required

Reference: Cache-Augmented Generation reduces latency by 40x compared to RAG
for small, stable knowledge bases that fit in the context window.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
import tiktoken  # For accurate token counting
import psutil  # For system memory detection

# Document processing - import from rag-system directory
import sys
from pathlib import Path as PathLib
sys.path.insert(0, str(PathLib(__file__).parent / "rag-system"))
from document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_optimal_cag_capacity() -> int:
    """
    Calculate optimal CAG token capacity based on available system memory.

    Strategy:
    - Get available system RAM
    - Reserve 2GB minimum for OS and other processes
    - Estimate 6 bytes per token (text + metadata + overhead)
    - Cap at model context window limits (200K tokens for modern LLMs)
    - Minimum of 32K tokens for usability

    Returns:
        Optimal token capacity for CAG system
    """
    try:
        # Get system memory info
        memory = psutil.virtual_memory()
        total_ram_gb = memory.total / (1024 ** 3)
        available_ram_gb = memory.available / (1024 ** 3)

        # Calculate usable RAM for CAG (reserve 2GB minimum for system)
        reserved_ram_gb = max(2.0, total_ram_gb * 0.25)  # Reserve 25% or 2GB, whichever is larger
        usable_ram_gb = max(0.5, available_ram_gb - reserved_ram_gb)

        # Convert to bytes
        usable_ram_bytes = usable_ram_gb * (1024 ** 3)

        # Estimate tokens: ~6 bytes per token (text storage + metadata + Python overhead)
        bytes_per_token = 6
        estimated_tokens = int(usable_ram_bytes / bytes_per_token)

        # Apply constraints
        min_tokens = 32_000   # Minimum 32K for usability
        max_tokens = 200_000  # Modern LLM limit (e.g., Claude 3, GPT-4)

        optimal_tokens = max(min_tokens, min(estimated_tokens, max_tokens))

        logger.info(
            f"CAG Capacity Calculation:\n"
            f"  Total RAM: {total_ram_gb:.2f} GB\n"
            f"  Available RAM: {available_ram_gb:.2f} GB\n"
            f"  Usable for CAG: {usable_ram_gb:.2f} GB\n"
            f"  Estimated tokens: {estimated_tokens:,}\n"
            f"  Optimal capacity: {optimal_tokens:,} tokens"
        )

        return optimal_tokens

    except Exception as e:
        logger.warning(f"Failed to calculate optimal CAG capacity: {e}. Using default 128K.")
        return 128_000


class CAGManager:
    """
    Cache-Augmented Generation manager for in-memory context loading.

    Features:
    - Preload documents into memory with full text
    - Track token usage against context window limits
    - Direct context injection for LLM queries
    - Zero retrieval latency
    """

    def __init__(self, max_context_tokens: Optional[int] = None):
        """
        Initialize CAG manager.

        Args:
            max_context_tokens: Maximum tokens for context window. If None, calculates
                              optimal capacity based on available system memory.
        """
        if max_context_tokens is None:
            self.max_context_tokens = calculate_optimal_cag_capacity()
        else:
            self.max_context_tokens = max_context_tokens
        self.cached_documents: Dict[str, Dict[str, Any]] = {}
        self.total_tokens = 0

        # Initialize document processor
        self.doc_processor = DocumentProcessor()

        # Initialize tokenizer for accurate counting
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            # Fallback to cl100k_base encoding
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        logger.info(f"CAG Manager initialized with {self.max_context_tokens:,} token capacity")

    def load_document(self, file_path: str) -> Dict[str, Any]:
        """
        Load a document into the CAG cache.

        Args:
            file_path: Path to document file

        Returns:
            Status dict with success/error and metadata
        """
        try:
            # Process document
            result = self.doc_processor.process_document(file_path)

            if result['status'] != 'success':
                return {
                    'status': 'error',
                    'error': result.get('error', 'Document processing failed')
                }

            # Combine all chunks into full text
            full_text = "\\n\\n".join([chunk['text'] for chunk in result['chunks']])

            # Count tokens
            tokens = self._count_tokens(full_text)

            # Check if it fits in available space
            available = self.max_context_tokens - self.total_tokens
            if tokens > available:
                return {
                    'status': 'error',
                    'error': f'Document requires {tokens} tokens, but only {available} available. Clear cache or remove documents.',
                    'tokens_required': tokens,
                    'tokens_available': available
                }

            # Store in cache
            doc_id = Path(file_path).stem
            self.cached_documents[doc_id] = {
                'id': doc_id,
                'filename': Path(file_path).name,
                'file_path': file_path,
                'file_type': result.get('file_type', 'unknown'),
                'content': full_text,
                'tokens': tokens,
                'loaded_at': datetime.now().isoformat(),
                'status': 'cached'
            }

            self.total_tokens += tokens

            logger.info(f"✅ Loaded {Path(file_path).name} into CAG cache ({tokens} tokens)")

            return {
                'status': 'success',
                'doc_id': doc_id,
                'filename': Path(file_path).name,
                'tokens': tokens,
                'total_tokens': self.total_tokens,
                'available_tokens': self.max_context_tokens - self.total_tokens,
                'usage_percent': (self.total_tokens / self.max_context_tokens) * 100
            }

        except Exception as e:
            logger.error(f"Error loading document to CAG: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def remove_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Remove a document from the CAG cache.

        Args:
            doc_id: Document ID to remove

        Returns:
            Status dict
        """
        if doc_id not in self.cached_documents:
            return {
                'status': 'error',
                'error': f'Document {doc_id} not found in cache'
            }

        doc = self.cached_documents[doc_id]
        tokens = doc['tokens']

        del self.cached_documents[doc_id]
        self.total_tokens -= tokens

        logger.info(f"🗑️ Removed {doc['filename']} from CAG cache (freed {tokens} tokens)")

        return {
            'status': 'success',
            'removed': doc['filename'],
            'tokens_freed': tokens,
            'total_tokens': self.total_tokens,
            'available_tokens': self.max_context_tokens - self.total_tokens
        }

    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear all cached documents.

        Returns:
            Status dict
        """
        docs_count = len(self.cached_documents)
        tokens_freed = self.total_tokens

        self.cached_documents = {}
        self.total_tokens = 0

        logger.info(f"🧹 Cleared CAG cache ({docs_count} documents, {tokens_freed} tokens)")

        return {
            'status': 'success',
            'documents_removed': docs_count,
            'tokens_freed': tokens_freed,
            'total_tokens': 0,
            'available_tokens': self.max_context_tokens
        }

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status and statistics.

        Returns:
            Cache status dict
        """
        return {
            'total_tokens': self.total_tokens,
            'available_tokens': self.max_context_tokens - self.total_tokens,
            'max_tokens': self.max_context_tokens,
            'usage_percent': (self.total_tokens / self.max_context_tokens) * 100,
            'document_count': len(self.cached_documents),
            'documents': [
                {
                    'id': doc['id'],
                    'filename': doc['filename'],
                    'tokens': doc['tokens'],
                    'loaded_at': doc['loaded_at'],
                    'status': doc['status']
                }
                for doc in self.cached_documents.values()
            ]
        }

    def get_context_for_query(self, query: str, include_query: bool = True) -> str:
        """
        Build the full context string for an LLM query.

        Args:
            query: User query
            include_query: Whether to include the query in the context

        Returns:
            Full context string to send to LLM
        """
        if not self.cached_documents:
            return query if include_query else ""

        # Build context from all cached documents
        context_parts = ["# Preloaded Knowledge Context\\n"]

        for doc in self.cached_documents.values():
            context_parts.append(f"## {doc['filename']}\\n")
            context_parts.append(doc['content'])
            context_parts.append("\\n---\\n")

        context_parts.append("\\n# User Query\\n")

        if include_query:
            context_parts.append(query)

        full_context = "\\n".join(context_parts)

        return full_context

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            # Fallback to rough estimation (1 token ≈ 4 chars)
            logger.warning(f"Token counting failed, using estimation: {e}")
            return len(text) // 4


# Global CAG manager instance
_cag_manager: Optional[CAGManager] = None


def get_cag_manager() -> CAGManager:
    """Get or create the global CAG manager instance."""
    global _cag_manager
    if _cag_manager is None:
        _cag_manager = CAGManager()
    return _cag_manager


def test_cag_system():
    """Test the CAG system with sample documents."""
    manager = CAGManager()

    # Create test document
    test_file = Path("./test_cag_doc.txt")
    test_file.write_text("""
    CAG (Cache-Augmented Generation) Test Document

    This document demonstrates the CAG system's ability to preload
    knowledge directly into the model's context window.

    Key Benefits:
    1. Zero retrieval latency (40x faster than RAG)
    2. Perfect accuracy for cached content
    3. Simplified architecture (no vector DB needed)
    4. Ideal for stable, small knowledge bases

    Use cases:
    - Product documentation
    - Standard operating procedures
    - Reference materials
    - Company policies
    """)

    # Test loading
    result = manager.load_document(str(test_file))
    print("Load Result:", json.dumps(result, indent=2))

    # Test status
    status = manager.get_cache_status()
    print("\\nCache Status:", json.dumps(status, indent=2))

    # Test context building
    context = manager.get_context_for_query("What are the benefits of CAG?")
    print("\\nGenerated Context:")
    print(context)

    # Cleanup
    test_file.unlink()


if __name__ == "__main__":
    test_cag_system()
