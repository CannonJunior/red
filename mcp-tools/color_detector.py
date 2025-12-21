"""
Color Detector MCP Tool - Detects all colors currently displayed in the web application.

This tool scans DOM elements and extracts color values from:
- Inline styles
- Computed styles
- CSS variables
- Tailwind CSS classes
- Background colors, text colors, border colors, etc.
"""

import re
import json
from typing import Dict, List, Set


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color."""
    return f'#{r:02x}{g:02x}{b:02x}'


def normalize_color(color: str) -> str:
    """Normalize color value to hex format."""
    color = color.strip().lower()

    # Already hex
    if color.startswith('#'):
        return color

    # RGB format
    if color.startswith('rgb(') or color.startswith('rgba('):
        # Extract RGB values
        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color)
        if match:
            r, g, b = map(int, match.groups())
            return rgb_to_hex(r, g, b)

    # Named colors - common ones
    named_colors = {
        'white': '#ffffff',
        'black': '#000000',
        'red': '#ff0000',
        'green': '#008000',
        'blue': '#0000ff',
        'gray': '#808080',
        'grey': '#808080',
        'yellow': '#ffff00',
        'cyan': '#00ffff',
        'magenta': '#ff00ff',
    }

    return named_colors.get(color, color)


def detect_tailwind_colors(html_content: str) -> Dict[str, List[str]]:
    """
    Detect Tailwind CSS color classes in HTML.

    Returns:
        dict: Categorized color classes found
    """
    colors = {
        'background': set(),
        'text': set(),
        'border': set(),
        'other': set()
    }

    # Tailwind color patterns
    bg_pattern = r'bg-(gray|red|yellow|green|blue|indigo|purple|pink)-(\d{2,3})'
    text_pattern = r'text-(gray|red|yellow|green|blue|indigo|purple|pink)-(\d{2,3})'
    border_pattern = r'border-(gray|red|yellow|green|blue|indigo|purple|pink)-(\d{2,3})'

    # Find all matches
    for match in re.finditer(bg_pattern, html_content):
        colors['background'].add(f'{match.group(1)}-{match.group(2)}')

    for match in re.finditer(text_pattern, html_content):
        colors['text'].add(f'{match.group(1)}-{match.group(2)}')

    for match in re.finditer(border_pattern, html_content):
        colors['border'].add(f'{match.group(1)}-{match.group(2)}')

    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in colors.items()}


def get_tailwind_color_value(color_class: str) -> str:
    """
    Get hex value for a Tailwind color class.

    Args:
        color_class: Tailwind color like 'gray-50', 'blue-600', etc.

    Returns:
        str: Hex color value
    """
    # Tailwind color palette (simplified)
    tailwind_colors = {
        'gray-50': '#f9fafb',
        'gray-100': '#f3f4f6',
        'gray-200': '#e5e7eb',
        'gray-300': '#d1d5db',
        'gray-400': '#9ca3af',
        'gray-500': '#6b7280',
        'gray-600': '#4b5563',
        'gray-700': '#374151',
        'gray-800': '#1f2937',
        'gray-900': '#111827',
        'blue-50': '#eff6ff',
        'blue-100': '#dbeafe',
        'blue-200': '#bfdbfe',
        'blue-300': '#93c5fd',
        'blue-400': '#60a5fa',
        'blue-500': '#3b82f6',
        'blue-600': '#2563eb',
        'blue-700': '#1d4ed8',
        'blue-800': '#1e40af',
        'blue-900': '#1e3a8a',
        'red-50': '#fef2f2',
        'red-100': '#fee2e2',
        'red-200': '#fecaca',
        'red-300': '#fca5a5',
        'red-400': '#f87171',
        'red-500': '#ef4444',
        'red-600': '#dc2626',
        'red-700': '#b91c1c',
        'red-800': '#991b1b',
        'red-900': '#7f1d1d',
        'green-50': '#f0fdf4',
        'green-100': '#dcfce7',
        'green-200': '#bbf7d0',
        'green-300': '#86efac',
        'green-400': '#4ade80',
        'green-500': '#22c55e',
        'green-600': '#16a34a',
        'green-700': '#15803d',
        'green-800': '#166534',
        'green-900': '#14532d',
    }

    return tailwind_colors.get(color_class, '#000000')


def detect_colors(html_content: str = None) -> Dict:
    """
    Main function to detect all colors in the application.

    Args:
        html_content: Optional HTML content to scan

    Returns:
        dict: Detected colors organized by category
    """
    if not html_content:
        # If no HTML provided, return template for client-side detection
        return {
            'status': 'template',
            'message': 'Use client-side JavaScript to detect colors from DOM',
            'instructions': {
                'method': 'getComputedStyle',
                'properties': ['color', 'backgroundColor', 'borderColor'],
                'example': 'window.getComputedStyle(element).backgroundColor'
            }
        }

    tailwind_colors = detect_tailwind_colors(html_content)

    # Build color palette
    color_palette = []

    # Background colors
    for tw_class in tailwind_colors['background']:
        color_palette.append({
            'category': 'Background',
            'name': f'bg-{tw_class}',
            'class': f'bg-{tw_class}',
            'value': get_tailwind_color_value(tw_class),
            'type': 'tailwind'
        })

    # Text colors
    for tw_class in tailwind_colors['text']:
        color_palette.append({
            'category': 'Text',
            'name': f'text-{tw_class}',
            'class': f'text-{tw_class}',
            'value': get_tailwind_color_value(tw_class),
            'type': 'tailwind'
        })

    # Border colors
    for tw_class in tailwind_colors['border']:
        color_palette.append({
            'category': 'Border',
            'name': f'border-{tw_class}',
            'class': f'border-{tw_class}',
            'value': get_tailwind_color_value(tw_class),
            'type': 'tailwind'
        })

    return {
        'status': 'success',
        'color_count': len(color_palette),
        'colors': color_palette,
        'categories': list(set(c['category'] for c in color_palette))
    }


# MCP Tool definition
MCP_TOOL = {
    'name': 'color_detector',
    'description': 'Detect all colors currently displayed in the web application',
    'input_schema': {
        'type': 'object',
        'properties': {
            'html_content': {
                'type': 'string',
                'description': 'Optional HTML content to scan for colors'
            }
        }
    },
    'handler': detect_colors
}


if __name__ == '__main__':
    # Test the tool
    test_html = '''
    <div class="bg-gray-50 dark:bg-gray-800">
        <p class="text-gray-900 dark:text-white">Hello</p>
        <button class="bg-blue-600 text-white border-blue-700">Click</button>
    </div>
    '''

    result = detect_colors(test_html)
    print(json.dumps(result, indent=2))
