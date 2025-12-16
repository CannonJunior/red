"""Natural Language Processing parser for TODO items.

This module provides intelligent parsing of natural language input to extract
structured todo data including dates, times, priorities, tags, and buckets.

Examples:
    - "Submit report by Friday 3pm @high #work"
    - "Call mom tomorrow"
    - "Review PR in 3 days @urgent"
    - "Buy groceries today #personal"
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class TodoNLPParser:
    """Parse natural language input into structured todo data.

    Extracts:
        - Title: Clean task description
        - Tags: Hashtag markers (#tag)
        - Priority: @high, @urgent, @low, @medium, !, !!
        - Due date: today, tomorrow, weekdays, "in X days", ISO dates
        - Due time: 3pm, 12:00, 3:00 pm
        - Bucket: inbox, today, upcoming, someday
    """

    # Priority markers and their mappings
    PRIORITY_MARKERS = {
        '@high': 'high',
        '@urgent': 'urgent',
        '@medium': 'medium',
        '@low': 'low',
        '!!': 'urgent',
        '!': 'high',
    }

    # Weekday names for date parsing
    WEEKDAYS = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6,
        'mon': 0,
        'tue': 1,
        'wed': 2,
        'thu': 3,
        'fri': 4,
        'sat': 5,
        'sun': 6,
    }

    def __init__(self):
        """Initialize the NLP parser."""
        pass

    def parse(self, input_text: str, user_id: Optional[str] = None) -> Dict:
        """Parse natural language input into structured todo data.

        Args:
            input_text: Natural language todo description
            user_id: Optional user ID for context

        Returns:
            Dictionary with parsed todo fields

        Example:
            >>> parser = TodoNLPParser()
            >>> result = parser.parse("Submit report by Friday 3pm @high #work")
            >>> result['title']
            'Submit report'
            >>> result['priority']
            'high'
        """
        if not input_text or not input_text.strip():
            return {
                'title': '',
                'tags': [],
                'priority': 'medium',
                'due_date': None,
                'due_time': None,
                'bucket': 'inbox',
                'description': None
            }

        # Initialize result structure
        result = {
            'title': '',
            'tags': [],
            'priority': 'medium',
            'due_date': None,
            'due_time': None,
            'bucket': 'inbox',
            'description': None
        }

        # Work with a mutable copy
        remaining_text = input_text.strip()

        # Extract tags first (#tag)
        remaining_text, tags = self._extract_tags(remaining_text)
        result['tags'] = tags

        # Extract priority markers (@high, !, !!)
        remaining_text, priority = self._extract_priority(remaining_text)
        result['priority'] = priority

        # Extract date information (today, tomorrow, Friday, etc.)
        remaining_text, date_str = self._extract_date(remaining_text)
        if date_str:
            result['due_date'] = date_str
            result['bucket'] = self._determine_bucket(date_str)

        # Extract time information (3pm, 12:00, etc.)
        remaining_text, time_str = self._extract_time(remaining_text)
        if time_str:
            result['due_time'] = time_str

        # Clean up and set title
        result['title'] = self._clean_title(remaining_text)

        return result

    def _extract_tags(self, text: str) -> Tuple[str, List[str]]:
        """Extract hashtag tags from text.

        Args:
            text: Input text

        Returns:
            Tuple of (remaining_text, list_of_tags)
        """
        tags = re.findall(r'#(\w+)', text)
        # Remove tags from text
        cleaned_text = re.sub(r'#\w+', '', text)
        return cleaned_text.strip(), tags

    def _extract_priority(self, text: str) -> Tuple[str, str]:
        """Extract priority markers from text.

        Args:
            text: Input text

        Returns:
            Tuple of (remaining_text, priority_level)
        """
        priority = 'medium'  # Default priority
        remaining_text = text

        # Check for priority markers (order matters - check !! before !)
        for marker in ['!!', '!', '@urgent', '@high', '@medium', '@low']:
            if marker in text:
                priority = self.PRIORITY_MARKERS[marker]
                remaining_text = text.replace(marker, '', 1)  # Remove first occurrence
                break

        return remaining_text.strip(), priority

    def _extract_date(self, text: str) -> Tuple[str, Optional[str]]:
        """Extract date information from text.

        Args:
            text: Input text

        Returns:
            Tuple of (remaining_text, iso_date_string)
        """
        text_lower = text.lower()
        remaining_text = text
        date_obj = None

        # Pattern 1: "today"
        if re.search(r'\btoday\b', text_lower):
            date_obj = datetime.now()
            remaining_text = re.sub(r'\btoday\b', '', remaining_text, flags=re.IGNORECASE)

        # Pattern 2: "tomorrow"
        elif re.search(r'\btomorrow\b', text_lower):
            date_obj = datetime.now() + timedelta(days=1)
            remaining_text = re.sub(r'\btomorrow\b', '', remaining_text, flags=re.IGNORECASE)

        # Pattern 3: "next week"
        elif re.search(r'\bnext week\b', text_lower):
            date_obj = datetime.now() + timedelta(weeks=1)
            remaining_text = re.sub(r'\bnext week\b', '', remaining_text, flags=re.IGNORECASE)

        # Pattern 4: "in X days"
        else:
            match = re.search(r'\bin (\d+) days?\b', text_lower)
            if match:
                days = int(match.group(1))
                date_obj = datetime.now() + timedelta(days=days)
                remaining_text = re.sub(r'\bin \d+ days?\b', '', remaining_text, flags=re.IGNORECASE)

            # Pattern 5: Weekday names (Monday, Tuesday, etc.)
            else:
                for weekday_name, weekday_num in self.WEEKDAYS.items():
                    pattern = r'\b' + weekday_name + r'\b'
                    if re.search(pattern, text_lower):
                        date_obj = self._next_weekday(weekday_num)
                        remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
                        break

            # Pattern 6: ISO date format (YYYY-MM-DD)
            if not date_obj:
                match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
                if match:
                    try:
                        date_obj = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                        remaining_text = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', remaining_text)
                    except ValueError:
                        pass  # Invalid date

        # Remove common date prepositions
        remaining_text = re.sub(r'\b(by|on|at)\b', '', remaining_text, flags=re.IGNORECASE)

        date_str = date_obj.strftime('%Y-%m-%d') if date_obj else None
        return remaining_text.strip(), date_str

    def _extract_time(self, text: str) -> Tuple[str, Optional[str]]:
        """Extract time information from text.

        Args:
            text: Input text

        Returns:
            Tuple of (remaining_text, time_string_HH:MM)
        """
        remaining_text = text
        time_str = None

        # Pattern 1: HH:MM am/pm or HH:MM (24-hour)
        match = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', text, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).lower() if match.group(3) else None

            # Convert to 24-hour format
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0

            # Validate time
            if 0 <= hour < 24 and 0 <= minute < 60:
                time_str = f"{hour:02d}:{minute:02d}"
                remaining_text = re.sub(r'\b\d{1,2}:\d{2}\s*(am|pm)?\b', '', remaining_text, flags=re.IGNORECASE)

        # Pattern 2: Simple format like "3pm" or "11am"
        else:
            match = re.search(r'\b(\d{1,2})\s*(am|pm)\b', text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                period = match.group(2).lower()

                # Convert to 24-hour format
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0

                # Validate hour
                if 0 <= hour < 24:
                    time_str = f"{hour:02d}:00"
                    remaining_text = re.sub(r'\b\d{1,2}\s*(am|pm)\b', '', remaining_text, flags=re.IGNORECASE)

        return remaining_text.strip(), time_str

    def _next_weekday(self, target_weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday.

        Args:
            target_weekday: Target weekday (0=Monday, 6=Sunday)

        Returns:
            DateTime object for next occurrence
        """
        today = datetime.now()
        current_weekday = today.weekday()

        # Calculate days until target weekday
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        return today + timedelta(days=days_ahead)

    def _determine_bucket(self, date_str: str) -> str:
        """Determine the appropriate bucket based on due date.

        Args:
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            Bucket name: 'today', 'upcoming', or 'inbox'
        """
        if not date_str:
            return 'inbox'

        try:
            due_date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Check if due today
            if due_date.date() == today.date():
                return 'today'

            # Check if due within next 7 days
            week_from_now = today + timedelta(days=7)
            if today < due_date <= week_from_now:
                return 'upcoming'

            # Everything else goes to upcoming
            return 'upcoming'

        except ValueError:
            return 'inbox'

    def _clean_title(self, text: str) -> str:
        """Clean up the title text by removing extra whitespace.

        Args:
            text: Input text

        Returns:
            Cleaned title string
        """
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        cleaned = cleaned.strip()

        # Remove trailing punctuation used for dates (by, on, at)
        cleaned = re.sub(r'\s+(by|on|at)\s*$', '', cleaned, flags=re.IGNORECASE)

        return cleaned


def parse_natural_language(input_text: str, user_id: Optional[str] = None) -> Dict:
    """Convenience function to parse natural language input.

    Args:
        input_text: Natural language todo description
        user_id: Optional user ID for context

    Returns:
        Dictionary with parsed todo fields
    """
    parser = TodoNLPParser()
    return parser.parse(input_text, user_id)
