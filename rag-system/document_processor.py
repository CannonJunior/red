"""
Document Processing Module using Docling for zero-cost, high-accuracy extraction.

This module provides local document processing capabilities following the 
OPTIMAL_RAG_IMPLEMENTATION_PLAN.md architecture, achieving 97.9% accuracy
without paid API services.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# Document processing imports
from docling.document_converter import DocumentConverter
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Zero-cost document processing using Docling and local AI models.
    Supports .txt, .pdf, .doc, .csv, .xls with intelligent chunking.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize Docling converter (free, 97.9% accuracy)
        self.converter = DocumentConverter()
        
        logger.info("DocumentProcessor initialized with zero-cost processing")
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process document based on file type (Agent-accessible via MCP).
        
        Args:
            file_path: Path to document file
            
        Returns:
            Processed document with chunks and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
                "chunks": []
            }
        
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.txt':
                return self._process_text_file(file_path)
            elif file_ext == '.pdf':
                return self._process_pdf_file(file_path)
            elif file_ext in ['.doc', '.docx']:
                return self._process_word_file(file_path)
            elif file_ext in ['.csv', '.xls', '.xlsx']:
                return self._process_spreadsheet_file(file_path)
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported file type: {file_ext}",
                    "chunks": []
                }
                
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "chunks": []
            }
    
    def _process_text_file(self, file_path: Path) -> Dict[str, Any]:
        """Process plain text files."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if content is empty
        if not content or not content.strip():
            return {
                "status": "error",
                "error": "Text file is empty or contains only whitespace",
                "file_path": str(file_path),
                "file_type": "text",
                "chunks": []
            }

        chunks = self._chunk_text(content)

        # Check if chunking produced any results
        if not chunks:
            return {
                "status": "error",
                "error": "Text file processing produced no usable chunks",
                "file_path": str(file_path),
                "file_type": "text",
                "chunks": []
            }

        return {
            "status": "success",
            "file_path": str(file_path),
            "file_type": "text",
            "total_chunks": len(chunks),
            "chunks": [{
                "text": chunk,
                "metadata": {
                    "source": str(file_path),
                    "chunk_index": i,
                    "file_type": "text"
                }
            } for i, chunk in enumerate(chunks)]
        }
    
    def _process_pdf_file(self, file_path: Path) -> Dict[str, Any]:
        """Process PDF files using Docling (97.9% accuracy, zero cost)."""
        try:
            # Convert PDF using Docling
            result = self.converter.convert(str(file_path))

            # Extract text content using export_to_markdown()
            content = result.document.export_to_markdown()

            # Check if content is empty
            if not content or not content.strip():
                return {
                    "status": "error",
                    "error": "PDF contains no extractable text content",
                    "file_path": str(file_path),
                    "file_type": "pdf",
                    "chunks": []
                }

            # Create chunks
            chunks = self._chunk_text(content)

            # Check if chunking produced any results
            if not chunks:
                return {
                    "status": "error",
                    "error": "PDF processing produced no usable chunks",
                    "file_path": str(file_path),
                    "file_type": "pdf",
                    "chunks": []
                }

            return {
                "status": "success",
                "file_path": str(file_path),
                "file_type": "pdf",
                "total_chunks": len(chunks),
                "processing_method": "docling",
                "chunks": [{
                    "text": chunk,
                    "metadata": {
                        "source": str(file_path),
                        "chunk_index": i,
                        "file_type": "pdf",
                        "processor": "docling"
                    }
                } for i, chunk in enumerate(chunks)]
            }

        except Exception as e:
            logger.error(f"Docling PDF processing failed: {e}")
            return {
                "status": "error",
                "error": f"PDF processing failed: {e}",
                "chunks": []
            }
    
    def _process_word_file(self, file_path: Path) -> Dict[str, Any]:
        """Process Word documents using Docling."""
        try:
            # Convert Word document using Docling
            result = self.converter.convert(str(file_path))

            # Extract text content using export_to_markdown()
            content = result.document.export_to_markdown()

            # Create chunks
            chunks = self._chunk_text(content)

            return {
                "status": "success",
                "file_path": str(file_path),
                "file_type": "word",
                "total_chunks": len(chunks),
                "processing_method": "docling",
                "chunks": [{
                    "text": chunk,
                    "metadata": {
                        "source": str(file_path),
                        "chunk_index": i,
                        "file_type": "word",
                        "processor": "docling"
                    }
                } for i, chunk in enumerate(chunks)]
            }

        except Exception as e:
            logger.error(f"Docling Word processing failed: {e}")
            return {
                "status": "error",
                "error": f"Word processing failed: {e}",
                "chunks": []
            }
    
    def _process_spreadsheet_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process spreadsheet files with intelligent semantic understanding.
        Addresses the complex spreadsheet vectorization challenge.
        """
        try:
            file_ext = file_path.suffix.lower()
            
            # Read spreadsheet
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            else:  # .xls, .xlsx
                df = pd.read_excel(file_path)
            
            chunks = []
            
            # Strategy 1: Table summary chunk
            summary_text = self._create_table_summary(df, file_path)
            chunks.append({
                "text": summary_text,
                "metadata": {
                    "source": str(file_path),
                    "chunk_index": 0,
                    "chunk_type": "table_summary",
                    "file_type": "spreadsheet",
                    "table_shape": f"{df.shape[0]}x{df.shape[1]}"
                }
            })
            
            # Strategy 2: Column-based semantic chunks
            for col_idx, col in enumerate(df.columns):
                col_text = self._create_column_chunk(df, col)
                chunks.append({
                    "text": col_text,
                    "metadata": {
                        "source": str(file_path),
                        "chunk_index": col_idx + 1,
                        "chunk_type": "column_summary",
                        "column_name": col,
                        "file_type": "spreadsheet"
                    }
                })
            
            # Strategy 3: Row-based chunks (for smaller datasets)
            if len(df) <= 100:  # Only for manageable datasets
                row_chunks = self._create_row_chunks(df, file_path)
                chunks.extend(row_chunks)
            
            return {
                "status": "success",
                "file_path": str(file_path),
                "file_type": "spreadsheet",
                "total_chunks": len(chunks),
                "processing_method": "intelligent_chunking",
                "table_info": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns)
                },
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Spreadsheet processing failed: {e}")
            return {
                "status": "error",
                "error": f"Spreadsheet processing failed: {e}",
                "chunks": []
            }
    
    def _create_table_summary(self, df: pd.DataFrame, file_path: Path) -> str:
        """Create a comprehensive table summary for semantic search."""
        summary_parts = [
            f"Spreadsheet: {file_path.name}",
            f"Dimensions: {len(df)} rows × {len(df.columns)} columns",
            "",
            "Column Overview:",
        ]
        
        for col in df.columns:
            col_info = f"- {col}: {df[col].dtype}"
            if df[col].dtype in ['int64', 'float64']:
                col_info += f" (range: {df[col].min()}-{df[col].max()})"
            elif df[col].dtype == 'object':
                unique_count = df[col].nunique()
                col_info += f" ({unique_count} unique values)"
                if unique_count <= 10:
                    col_info += f" - Examples: {', '.join(map(str, df[col].dropna().unique()[:5]))}"
            
            summary_parts.append(col_info)
        
        # Add sample data
        if len(df) > 0:
            summary_parts.extend([
                "",
                "Sample Data (first 3 rows):",
                df.head(3).to_string(index=False)
            ])
        
        return "\\n".join(summary_parts)
    
    def _create_column_chunk(self, df: pd.DataFrame, column: str) -> str:
        """Create a semantic chunk for a specific column."""
        col_data = df[column].dropna()
        
        chunk_parts = [
            f"Column Analysis: {column}",
            f"Data Type: {df[column].dtype}",
            f"Total Values: {len(col_data)} (excluding nulls)"
        ]
        
        if df[column].dtype in ['int64', 'float64']:
            chunk_parts.extend([
                f"Range: {col_data.min()} to {col_data.max()}",
                f"Mean: {col_data.mean():.2f}",
                f"Statistics: Min={col_data.min()}, Max={col_data.max()}, Mean={col_data.mean():.2f}"
            ])
        else:
            unique_values = col_data.unique()
            chunk_parts.extend([
                f"Unique Values: {len(unique_values)}",
                f"Sample Values: {', '.join(map(str, unique_values[:10]))}"
            ])
        
        return "\\n".join(chunk_parts)
    
    def _create_row_chunks(self, df: pd.DataFrame, file_path: Path) -> List[Dict[str, Any]]:
        """Create row-based chunks for detailed data access."""
        chunks = []
        
        for idx, row in df.iterrows():
            row_text = f"Row {idx + 1} from {file_path.name}:\\n"
            row_data = []
            
            for col, value in row.items():
                if pd.notna(value):
                    row_data.append(f"{col}: {value}")
            
            row_text += "\\n".join(row_data)
            
            chunks.append({
                "text": row_text,
                "metadata": {
                    "source": str(file_path),
                    "chunk_index": len(chunks) + len(df.columns) + 2,  # After summary and column chunks
                    "chunk_type": "data_row",
                    "row_index": idx,
                    "file_type": "spreadsheet"
                }
            })
        
        return chunks
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap for better context preservation.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                sentence_ends = [text.rfind('.', start, end),
                               text.rfind('!', start, end),
                               text.rfind('?', start, end)]
                valid_sentence_ends = [pos for pos in sentence_ends if pos > start + self.chunk_size // 2]

                # Only use sentence boundary if we found one
                if valid_sentence_ends:
                    sentence_end = max(valid_sentence_ends)
                    if sentence_end > 0:
                        end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
        return chunks


def test_document_processor():
    """Test function for document processing capabilities."""
    processor = DocumentProcessor()
    
    # Create test files
    test_dir = Path("./test_documents")
    test_dir.mkdir(exist_ok=True)
    
    # Test text file
    test_txt = test_dir / "test.txt"
    test_txt.write_text("""
    This is a test document for the RAG system.
    
    The system uses ChromaDB for vector storage and Ollama for local LLM integration.
    This provides zero-cost, high-performance document processing and retrieval.
    
    The document processor can handle multiple file types including PDF, Word, and spreadsheets.
    """)
    
    result = processor.process_document(str(test_txt))
    print("Text Processing Result:")
    print(json.dumps(result, indent=2))
    
    # Test CSV file
    test_csv = test_dir / "test.csv"
    test_data = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Age': [25, 30, 35],
        'Department': ['Engineering', 'Marketing', 'Engineering'],
        'Salary': [75000, 65000, 85000]
    })
    test_data.to_csv(test_csv, index=False)
    
    csv_result = processor.process_document(str(test_csv))
    print("\\nCSV Processing Result:")
    print(json.dumps(csv_result, indent=2))


if __name__ == "__main__":
    test_document_processor()