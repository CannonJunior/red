#!/usr/bin/env python3
"""
White Paper Review MCP Server
Editorial review system for user-supplied content with customizable grading rubrics.

Zero-cost, locally-running MCP server for document editorial review.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import mimetypes
from datetime import datetime

# MCP SDK imports
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: uv add mcp")
    sys.exit(1)

# Document processing imports
try:
    import docx
    from PyPDF2 import PdfReader
except ImportError:
    print("WARNING: Document processing libraries not fully installed")
    print("Install with: uv add python-docx PyPDF2")

# Ollama integration for LLM-based review
try:
    import urllib.request
    import urllib.parse
except ImportError:
    pass


class WhitePaperReviewServer:
    """
    MCP server for editorial review of white papers and documents.

    Features:
    - Custom grading rubrics
    - Multiple document format support (.txt, .doc, .docx, .pdf)
    - Directory batch processing
    - Configurable LLM model and response time
    - Zero-cost local operation using Ollama
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        default_model: str = "qwen2.5:3b",
        default_timeout: int = 30
    ):
        """
        Initialize the White Paper Review Server.

        Args:
            ollama_url: Ollama API endpoint
            default_model: Default LLM model for reviews
            default_timeout: Default timeout in seconds
        """
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.default_timeout = default_timeout
        self.mcp = FastMCP("whitepaper-review")

        # Register MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools for white paper review."""

        @self.mcp.tool()
        async def review_whitepaper(
            rubric_path: str,
            content_path: str,
            model: Optional[str] = None,
            timeout_seconds: Optional[int] = None,
            output_format: str = "markdown"
        ) -> str:
            """
            Review a white paper or document using a custom grading rubric.

            Args:
                rubric_path: Path to grading rubric file (.txt, .doc, .docx, .pdf, or directory)
                content_path: Path to content for review (.txt, .doc, .docx, .pdf, or directory)
                model: LLM model to use (default: qwen2.5:3b)
                timeout_seconds: Maximum response time in seconds (default: 30)
                output_format: Output format - 'markdown', 'json', or 'text' (default: markdown)

            Returns:
                Editorial review results based on the grading rubric
            """
            # Use defaults if not provided
            model = model or self.default_model
            timeout_seconds = timeout_seconds or self.default_timeout

            try:
                # Load rubric
                rubric_text = await self._load_document_or_directory(rubric_path)
                if not rubric_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load rubric from: {rubric_path}"
                    })

                # Load content
                content_text = await self._load_document_or_directory(content_path)
                if not content_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load content from: {content_path}"
                    })

                # Perform review using LLM
                review_result = await self._perform_review(
                    rubric=rubric_text,
                    content=content_text,
                    model=model,
                    timeout=timeout_seconds
                )

                # Format output
                formatted_result = self._format_output(
                    review_result,
                    output_format,
                    rubric_path,
                    content_path
                )

                return formatted_result

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Review failed: {str(e)}"
                })

        @self.mcp.tool()
        async def batch_review(
            rubric_path: str,
            content_directory: str,
            model: Optional[str] = None,
            timeout_seconds: Optional[int] = None,
            file_extensions: Optional[List[str]] = None
        ) -> str:
            """
            Batch review multiple documents in a directory.

            Args:
                rubric_path: Path to grading rubric file
                content_directory: Directory containing documents to review
                model: LLM model to use (default: qwen2.5:3b)
                timeout_seconds: Maximum response time per document (default: 30)
                file_extensions: File extensions to process (default: ['.txt', '.pdf', '.doc', '.docx'])

            Returns:
                Batch review results in JSON format
            """
            model = model or self.default_model
            timeout_seconds = timeout_seconds or self.default_timeout
            file_extensions = file_extensions or ['.txt', '.pdf', '.doc', '.docx']

            try:
                # Load rubric
                rubric_text = await self._load_document_or_directory(rubric_path)
                if not rubric_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load rubric from: {rubric_path}"
                    })

                # Find all documents in directory
                content_dir = Path(content_directory)
                if not content_dir.is_dir():
                    return json.dumps({
                        "status": "error",
                        "message": f"Content directory not found: {content_directory}"
                    })

                results = []
                for file_path in content_dir.iterdir():
                    if file_path.suffix.lower() in file_extensions:
                        try:
                            # Load document
                            content_text = await self._load_single_document(str(file_path))

                            # Review document
                            review_result = await self._perform_review(
                                rubric=rubric_text,
                                content=content_text,
                                model=model,
                                timeout=timeout_seconds
                            )

                            results.append({
                                "file": file_path.name,
                                "status": "success",
                                "review": review_result
                            })
                        except Exception as e:
                            results.append({
                                "file": file_path.name,
                                "status": "error",
                                "message": str(e)
                            })

                return json.dumps({
                    "status": "success",
                    "total_documents": len(results),
                    "results": results
                }, indent=2)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Batch review failed: {str(e)}"
                })

    async def _load_document_or_directory(self, path: str) -> Optional[str]:
        """
        Load document(s) from a file or directory.

        Args:
            path: File path or directory path

        Returns:
            Combined text content from document(s)
        """
        path_obj = Path(path)

        if not path_obj.exists():
            return None

        if path_obj.is_file():
            return await self._load_single_document(path)
        elif path_obj.is_dir():
            # Load all supported documents in directory
            combined_text = []
            for file_path in path_obj.iterdir():
                if file_path.suffix.lower() in ['.txt', '.pdf', '.doc', '.docx']:
                    try:
                        text = await self._load_single_document(str(file_path))
                        if text:
                            combined_text.append(f"--- {file_path.name} ---\n{text}\n")
                    except Exception as e:
                        print(f"Warning: Could not load {file_path.name}: {e}")

            return "\n".join(combined_text) if combined_text else None

        return None

    async def _load_single_document(self, file_path: str) -> Optional[str]:
        """
        Load a single document file.

        Args:
            file_path: Path to document file

        Returns:
            Text content of the document
        """
        file_path_obj = Path(file_path)
        suffix = file_path_obj.suffix.lower()

        try:
            if suffix == '.txt':
                # Plain text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            elif suffix == '.pdf':
                # PDF using PyPDF2
                reader = PdfReader(file_path)
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                return "\n".join(text_parts)

            elif suffix in ['.doc', '.docx']:
                # Word document using python-docx
                doc = docx.Document(file_path)
                text_parts = []
                for paragraph in doc.paragraphs:
                    text_parts.append(paragraph.text)
                return "\n".join(text_parts)

            else:
                print(f"Warning: Unsupported file type: {suffix}")
                return None

        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    async def _perform_review(
        self,
        rubric: str,
        content: str,
        model: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Perform editorial review using LLM.

        Args:
            rubric: Grading rubric text
            content: Content to review
            model: LLM model name
            timeout: Timeout in seconds

        Returns:
            Review results dictionary
        """
        # Construct review prompt
        prompt = f"""You are an expert editorial reviewer. Review the following content according to the provided grading rubric.

GRADING RUBRIC:
{rubric}

CONTENT TO REVIEW:
{content}

Provide a comprehensive editorial review that:
1. Evaluates the content against each criterion in the rubric
2. Assigns scores/grades where applicable
3. Provides specific examples from the content
4. Offers constructive feedback and improvement suggestions
5. Summarizes overall strengths and weaknesses

Please structure your review clearly with sections corresponding to the rubric criteria."""

        # Call Ollama API
        try:
            request_data = {
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9
                }
            }

            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(request_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            # Set timeout
            response = urllib.request.urlopen(req, timeout=timeout)
            result = json.loads(response.read().decode('utf-8'))

            return {
                "review_text": result.get('response', 'No response generated'),
                "model_used": model,
                "timestamp": datetime.now().isoformat(),
                "tokens_used": {
                    "prompt": result.get('prompt_eval_count', 0),
                    "completion": result.get('eval_count', 0),
                    "total": result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                }
            }

        except urllib.error.URLError as e:
            raise Exception(f"Ollama API connection failed: {e.reason}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid response from Ollama: {e}")
        except Exception as e:
            raise Exception(f"Review generation failed: {str(e)}")

    def _format_output(
        self,
        review_result: Dict[str, Any],
        output_format: str,
        rubric_path: str,
        content_path: str
    ) -> str:
        """
        Format review output according to requested format.

        Args:
            review_result: Review results dictionary
            output_format: Desired output format ('markdown', 'json', 'text')
            rubric_path: Path to rubric file
            content_path: Path to content file

        Returns:
            Formatted review output
        """
        if output_format == 'json':
            return json.dumps({
                "status": "success",
                "rubric": rubric_path,
                "content": content_path,
                "review": review_result
            }, indent=2)

        elif output_format == 'markdown':
            md = f"""# White Paper Editorial Review

**Date:** {review_result['timestamp']}
**Model:** {review_result['model_used']}
**Rubric:** {rubric_path}
**Content:** {content_path}

---

## Review

{review_result['review_text']}

---

## Metadata

- **Tokens Used:** {review_result['tokens_used']['total']}
  - Prompt: {review_result['tokens_used']['prompt']}
  - Completion: {review_result['tokens_used']['completion']}
"""
            return md

        else:  # text
            return review_result['review_text']

    async def run(self):
        """Run the MCP server."""
        print("🚀 Starting White Paper Review MCP Server...")
        print(f"📋 Ollama URL: {self.ollama_url}")
        print(f"🤖 Default Model: {self.default_model}")
        print(f"⏱️  Default Timeout: {self.default_timeout}s")
        print("✅ MCP Server ready for connections")

        await self.mcp.run()


async def main():
    """Main entry point for the MCP server."""
    # Read configuration from environment variables
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    default_model = os.getenv('DEFAULT_MODEL', 'qwen2.5:3b')
    default_timeout = int(os.getenv('DEFAULT_TIMEOUT', '30'))

    # Create and run server
    server = WhitePaperReviewServer(
        ollama_url=ollama_url,
        default_model=default_model,
        default_timeout=default_timeout
    )

    await server.run()


if __name__ == '__main__':
    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 White Paper Review MCP Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
