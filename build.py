#!/usr/bin/env python3
"""
Frontend Build Pipeline

Minifies JavaScript and CSS files, generates content hashes for cache busting,
and creates production-ready assets in the dist/ directory.

Features:
- JS/CSS minification with rjsmin and rcssmin
- Content-based hashing for cache busting
- Automatic index.html updates with hashed filenames
- Build statistics and file size comparisons
- Clean build directory management

Usage:
    python3 build.py              # Production build with minification
    python3 build.py --dev        # Development build (no minification)
    python3 build.py --clean      # Clean dist directory only
"""

import os
import sys
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Tuple
import rjsmin
import rcssmin


# Build configuration
SOURCE_DIR = Path(__file__).parent
DIST_DIR = SOURCE_DIR / "dist"
HASH_LENGTH = 8  # Length of content hash in filename

# Files to process
JS_FILES = [
    "app.js",
    "cag_manager.js",
    "mcp_agents.js",
    "prompts_manager.js"
]

CSS_FILES = [
    "styles.css"
]

HTML_FILE = "index.html"


def calculate_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content for cache busting.

    Args:
        content: File content as string

    Returns:
        str: First HASH_LENGTH characters of hex digest
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:HASH_LENGTH]


def format_size(size_bytes: int) -> str:
    """
    Format byte size as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size (e.g., "120.5 KB")
    """
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"


def minify_js(content: str) -> str:
    """
    Minify JavaScript content.

    Args:
        content: JavaScript source code

    Returns:
        str: Minified JavaScript
    """
    return rjsmin.jsmin(content)


def minify_css(content: str) -> str:
    """
    Minify CSS content.

    Args:
        content: CSS source code

    Returns:
        str: Minified CSS
    """
    return rcssmin.cssmin(content)


def process_file(
    filepath: str,
    minify: bool = True,
    file_type: str = "js"
) -> Tuple[str, str, int, int]:
    """
    Process a single file: read, minify, hash, and write to dist.

    Args:
        filepath: Path to source file
        minify: Whether to minify the file
        file_type: Type of file ("js" or "css")

    Returns:
        Tuple of (original_name, hashed_name, original_size, minified_size)
    """
    source_path = SOURCE_DIR / filepath

    # Read source file
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content.encode('utf-8'))

    # Minify if requested
    if minify:
        if file_type == "js":
            content = minify_js(content)
        elif file_type == "css":
            content = minify_css(content)

    minified_size = len(content.encode('utf-8'))

    # Calculate hash
    content_hash = calculate_hash(content)

    # Generate hashed filename
    name_parts = filepath.rsplit('.', 1)
    hashed_name = f"{name_parts[0]}.{content_hash}.{name_parts[1]}"

    # Write to dist directory
    dist_path = DIST_DIR / hashed_name
    with open(dist_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath, hashed_name, original_size, minified_size


def update_html(file_map: Dict[str, str]) -> Tuple[int, int]:
    """
    Update index.html with hashed filenames.

    Args:
        file_map: Mapping of original filename to hashed filename

    Returns:
        Tuple of (original_size, processed_size)
    """
    html_source = SOURCE_DIR / HTML_FILE
    html_dist = DIST_DIR / HTML_FILE

    # Read HTML
    with open(html_source, 'r', encoding='utf-8') as f:
        html_content = f.read()

    original_size = len(html_content.encode('utf-8'))

    # Replace filenames
    for original, hashed in file_map.items():
        html_content = html_content.replace(f'"{original}"', f'"dist/{hashed}"')
        html_content = html_content.replace(f"'{original}'", f"'dist/{hashed}'")

    processed_size = len(html_content.encode('utf-8'))

    # Write updated HTML to source directory (not dist)
    # This allows the server to serve the updated HTML from root
    with open(html_source, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return original_size, processed_size


def clean_dist():
    """Remove and recreate dist directory."""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(exist_ok=True)
    print(f"✓ Cleaned dist directory: {DIST_DIR}")


def build(minify: bool = True):
    """
    Run the full build pipeline.

    Args:
        minify: Whether to minify assets (False for dev builds)
    """
    print("=" * 60)
    print("Frontend Build Pipeline")
    print("=" * 60)
    print(f"Mode: {'PRODUCTION (minified)' if minify else 'DEVELOPMENT (unminified)'}")
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {DIST_DIR}")
    print()

    # Clean and create dist directory
    clean_dist()
    print()

    # Track file mappings and statistics
    file_map = {}
    total_original = 0
    total_minified = 0

    # Process JavaScript files
    print("Processing JavaScript files:")
    print("-" * 60)
    for js_file in JS_FILES:
        original, hashed, orig_size, min_size = process_file(
            js_file,
            minify=minify,
            file_type="js"
        )
        file_map[original] = hashed
        total_original += orig_size
        total_minified += min_size

        reduction = ((orig_size - min_size) / orig_size * 100) if orig_size > 0 else 0
        print(f"  {original}")
        print(f"    → {hashed}")
        print(f"    Size: {format_size(orig_size)} → {format_size(min_size)} ({reduction:.1f}% reduction)")

    print()

    # Process CSS files
    print("Processing CSS files:")
    print("-" * 60)
    for css_file in CSS_FILES:
        original, hashed, orig_size, min_size = process_file(
            css_file,
            minify=minify,
            file_type="css"
        )
        file_map[original] = hashed
        total_original += orig_size
        total_minified += min_size

        reduction = ((orig_size - min_size) / orig_size * 100) if orig_size > 0 else 0
        print(f"  {original}")
        print(f"    → {hashed}")
        print(f"    Size: {format_size(orig_size)} → {format_size(min_size)} ({reduction:.1f}% reduction)")

    print()

    # Update HTML
    print("Updating HTML:")
    print("-" * 60)
    html_orig, html_proc = update_html(file_map)
    print(f"  {HTML_FILE}")
    print(f"    Updated with hashed filenames")
    print(f"    Size: {format_size(html_orig)}")

    print()

    # Build summary
    print("=" * 60)
    print("Build Summary")
    print("=" * 60)
    print(f"Files processed: {len(file_map)}")
    print(f"Total original size: {format_size(total_original)}")
    print(f"Total minified size: {format_size(total_minified)}")

    total_reduction = ((total_original - total_minified) / total_original * 100) if total_original > 0 else 0
    print(f"Total reduction: {format_size(total_original - total_minified)} ({total_reduction:.1f}%)")
    print()
    print("✓ Build completed successfully!")
    print()


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if '--clean' in args:
        clean_dist()
        return

    if '--dev' in args:
        build(minify=False)
    else:
        build(minify=True)


if __name__ == "__main__":
    main()
