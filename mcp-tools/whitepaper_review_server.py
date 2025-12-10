#!/usr/bin/env python3
"""
White Paper Review MCP Server (Refactored)
Editorial review system for user-supplied content with customizable grading rubrics.

Zero-cost, locally-running MCP server for document editorial review.
Uses shared infrastructure from common/ modules.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# MCP SDK imports
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: uv add mcp")
    sys.exit(1)

# Shared infrastructure
try:
    from common.config import get_config
    from common.document_loader import DocumentLoader
    from common.ollama_client import OllamaClient
    from common.errors import DocumentLoadError, ExtractionError
except ImportError:
    print("ERROR: Shared infrastructure not available")
    print("Make sure common/ modules are in mcp-tools/common/")
    sys.exit(1)


class WhitePaperReviewServer:
    """
    MCP server for editorial review of white papers and documents.

    Features:
    - Custom grading rubrics
    - Multiple document format support (.txt, .doc, .docx, .pdf)
    - Directory batch processing
    - Configurable LLM model and response time
    - Zero-cost local operation using Ollama
    - Uses shared infrastructure (DocumentLoader, OllamaClient, MCPToolConfig)
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        default_model: Optional[str] = None,
        default_timeout: Optional[int] = None,
        config=None
    ):
        """
        Initialize the White Paper Review Server.

        Args:
            ollama_url: Ollama API endpoint (uses config default if None)
            default_model: Default LLM model (uses config default if None)
            default_timeout: Default timeout in seconds (uses config default if None)
            config: MCPToolConfig instance (creates if None)
        """
        # Use shared configuration
        self.config = config or get_config()

        # Allow override of specific settings for backwards compatibility
        self.ollama_url = ollama_url or self.config.ollama_url
        self.default_model = default_model or self.config.default_model
        self.default_timeout = default_timeout or self.config.default_timeout

        # Initialize shared modules
        self.document_loader = DocumentLoader(config=self.config)
        self.ollama_client = OllamaClient(config=self.config)

        # Initialize MCP
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
                timeout_seconds: Maximum response time in seconds (default: 120)
                output_format: Output format - 'markdown', 'json', or 'text' (default: markdown)

            Returns:
                Editorial review results based on the grading rubric
            """
            # Use defaults if not provided
            model = model or self.default_model
            timeout_seconds = timeout_seconds or self.default_timeout

            try:
                # Load rubric using shared DocumentLoader
                rubric_docs = await self.document_loader.load(rubric_path)
                rubric_text = self.document_loader.combine_documents(rubric_docs, strategy="concatenate")

                if not rubric_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load rubric from: {rubric_path}"
                    })

                # Load content using shared DocumentLoader
                content_docs = await self.document_loader.load(content_path)
                content_text = self.document_loader.combine_documents(content_docs, strategy="sections")

                if not content_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load content from: {content_path}"
                    })

                # Perform review using shared OllamaClient
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

            except DocumentLoadError as e:
                return json.dumps({
                    "status": "error",
                    "message": e.message,
                    "suggestions": e.suggestions
                })
            except ExtractionError as e:
                return json.dumps({
                    "status": "error",
                    "message": e.message,
                    "suggestions": e.suggestions
                })
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
                timeout_seconds: Maximum response time per document (default: 120)
                file_extensions: File extensions to process (default: ['.txt', '.pdf', '.doc', '.docx'])

            Returns:
                Batch review results in JSON format
            """
            model = model or self.default_model
            timeout_seconds = timeout_seconds or self.default_timeout
            file_extensions = file_extensions or self.config.supported_document_formats

            try:
                # Load rubric using shared DocumentLoader
                rubric_docs = await self.document_loader.load(rubric_path)
                rubric_text = self.document_loader.combine_documents(rubric_docs, strategy="concatenate")

                if not rubric_text:
                    return json.dumps({
                        "status": "error",
                        "message": f"Failed to load rubric from: {rubric_path}"
                    })

                # Load all documents from directory
                content_docs = await self.document_loader.load(
                    content_directory,
                    recursive=False,
                    formats=file_extensions
                )

                # Review each document
                results = []
                for doc in content_docs:
                    try:
                        # Review document
                        review_result = await self._perform_review(
                            rubric=rubric_text,
                            content=doc.text,
                            model=model,
                            timeout=timeout_seconds
                        )

                        results.append({
                            "file": doc.metadata.file_name,
                            "status": "success",
                            "review": review_result
                        })
                    except Exception as e:
                        results.append({
                            "file": doc.metadata.file_name,
                            "status": "error",
                            "message": str(e)
                        })

                return json.dumps({
                    "status": "success",
                    "total_documents": len(results),
                    "results": results
                }, indent=2)

            except DocumentLoadError as e:
                return json.dumps({
                    "status": "error",
                    "message": e.message,
                    "suggestions": e.suggestions
                })
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Batch review failed: {str(e)}"
                })

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
        # Record start time
        start_time = time.time()

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

        # Call Ollama using shared client
        try:
            response_text = await self.ollama_client.generate(
                prompt=prompt,
                model=model,
                timeout=timeout
            )

            # Calculate elapsed time
            elapsed_seconds = time.time() - start_time
            elapsed_minutes = int(elapsed_seconds // 60)
            elapsed_secs = int(elapsed_seconds % 60)
            elapsed_formatted = f"{elapsed_minutes}m {elapsed_secs}s" if elapsed_minutes > 0 else f"{elapsed_secs}s"

            return {
                "review_text": response_text or 'No response generated',
                "model_used": model,
                "timestamp": datetime.now().isoformat(),
                "elapsed_time": elapsed_formatted,
                "elapsed_seconds": elapsed_seconds,
                "tokens_used": {
                    "prompt": 0,  # Ollama client doesn't return token counts yet
                    "completion": 0,
                    "total": 0
                }
            }

        except ExtractionError as e:
            # Re-raise with review context
            raise Exception(f"Review generation failed: {e.message}")

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
**Elapsed Time:** {review_result.get('elapsed_time', 'N/A')}
**Rubric:** {rubric_path}
**Content:** {content_path}

---

## Review

{review_result['review_text']}

---

## Metadata

- **Model:** {review_result['model_used']}
- **Timestamp:** {review_result['timestamp']}
- **Elapsed Time:** {review_result.get('elapsed_time', 'N/A')}
"""
            return md

        else:  # text
            return review_result['review_text']

    async def run(self):
        """Run the MCP server."""
        print("🚀 Starting White Paper Review MCP Server (Refactored)...")
        print(f"📋 Ollama URL: {self.ollama_url}")
        print(f"🤖 Default Model: {self.default_model}")
        print(f"⏱️  Default Timeout: {self.default_timeout}s")
        print(f"💾 Cache Enabled: {self.config.enable_cache}")
        print(f"📂 Cache Dir: {self.config.cache_dir}")
        print("✅ MCP Server ready for connections")

        await self.mcp.run()


async def main():
    """Main entry point for the MCP server."""
    # Read configuration from environment variables (for backwards compatibility)
    ollama_url = os.getenv('OLLAMA_URL')
    default_model = os.getenv('DEFAULT_MODEL')
    default_timeout = int(os.getenv('DEFAULT_TIMEOUT', '0')) or None

    # Create and run server (will use MCPToolConfig defaults if env vars not set)
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
