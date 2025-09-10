"""
Universal Search System for Robobrain
Implements comprehensive search, filtering, and organization capabilities
across all object types (chats, documents, projects, models, knowledge bases).
"""

import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObjectType(Enum):
    CHAT = "chat"
    DOCUMENT = "document"
    PROJECT = "project"
    MODEL = "model"
    KNOWLEDGE_BASE = "knowledge_base"


class SharePermission(Enum):
    VIEW = "view"
    EDIT = "edit"
    COMMENT = "comment"


@dataclass
class SearchableObject:
    """Universal object model for searchable items."""
    id: str
    type: ObjectType
    title: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    folder_id: Optional[str] = None
    is_pinned: bool = False
    is_shared: bool = False
    is_archived: bool = False
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    author: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
        if self.created_date is None:
            self.created_date = datetime.now()
        if self.modified_date is None:
            self.modified_date = datetime.now()


@dataclass
class Folder:
    """Hierarchical folder structure for organizing objects."""
    id: str
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    object_types: List[ObjectType] = None
    created_date: Optional[datetime] = None
    is_shared: bool = False

    def __post_init__(self):
        if self.object_types is None:
            self.object_types = list(ObjectType)  # Allow all types by default
        if self.created_date is None:
            self.created_date = datetime.now()


@dataclass
class Tag:
    """Tag system for flexible categorization."""
    id: str
    name: str
    color: str = "#3B82F6"  # Default blue
    usage_count: int = 0
    created_date: Optional[datetime] = None
    auto_generated: bool = False

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()


@dataclass
class SearchFilter:
    """Search filter configuration."""
    query: str = ""
    object_types: List[ObjectType] = None
    tags: List[str] = None
    folder_ids: List[str] = None
    is_pinned: Optional[bool] = None
    is_shared: Optional[bool] = None
    is_archived: Optional[bool] = None
    author: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

    def __post_init__(self):
        if self.object_types is None:
            self.object_types = list(ObjectType)


class SearchDatabase:
    """SQLite-based database for the search system."""
    
    def __init__(self, db_path: str = "./search_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables with proper schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create searchable_objects table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS searchable_objects (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,  -- JSON
                    folder_id TEXT,
                    is_pinned BOOLEAN DEFAULT FALSE,
                    is_shared BOOLEAN DEFAULT FALSE,
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    author TEXT,
                    FOREIGN KEY (folder_id) REFERENCES folders(id)
                )
            """)
            
            # Create folders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_id TEXT,
                    color TEXT,
                    icon TEXT,
                    object_types TEXT,  -- JSON array
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_shared BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (parent_id) REFERENCES folders(id)
                )
            """)
            
            # Create tags table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#3B82F6',
                    usage_count INTEGER DEFAULT 0,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    auto_generated BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create object_tags junction table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS object_tags (
                    object_id TEXT,
                    tag_id TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (object_id, tag_id),
                    FOREIGN KEY (object_id) REFERENCES searchable_objects(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)
            
            # Create search indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_type ON searchable_objects(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_title ON searchable_objects(title)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_created ON searchable_objects(created_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_modified ON searchable_objects(modified_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_pinned ON searchable_objects(is_pinned)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_shared ON searchable_objects(is_shared)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_archived ON searchable_objects(is_archived)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_folder ON searchable_objects(folder_id)")
            
            # Create full-text search virtual table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS objects_fts USING fts5(
                    object_id,
                    title,
                    content,
                    tags,
                    content='searchable_objects',
                    content_rowid='rowid'
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")


class UniversalSearchSystem:
    """Main search system class with all functionality."""
    
    def __init__(self, db_path: str = "./search_system.db"):
        self.db = SearchDatabase(db_path)
    
    # Object Management
    def add_object(self, obj: SearchableObject) -> bool:
        """Add a searchable object to the system."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                # Insert object
                conn.execute("""
                    INSERT OR REPLACE INTO searchable_objects 
                    (id, type, title, content, metadata, folder_id, is_pinned, is_shared, is_archived, 
                     created_date, modified_date, author)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    obj.id, obj.type.value, obj.title, obj.content, 
                    json.dumps(obj.metadata) if obj.metadata else None,
                    obj.folder_id, obj.is_pinned, obj.is_shared, obj.is_archived,
                    obj.created_date.isoformat() if obj.created_date else None,
                    obj.modified_date.isoformat() if obj.modified_date else None,
                    obj.author
                ))
                
                # Add tags
                if obj.tags:
                    self._add_tags_to_object(conn, obj.id, obj.tags)
                
                # Update FTS
                self._update_fts(conn, obj)
                
                conn.commit()
                logger.info(f"Added object: {obj.id} ({obj.type.value})")
                return True
                
        except Exception as e:
            logger.error(f"Error adding object {obj.id}: {e}")
            return False
    
    def _add_tags_to_object(self, conn, object_id: str, tags: List[str]):
        """Add tags to an object, creating tags if they don't exist."""
        for tag_name in tags:
            # Create tag if it doesn't exist
            tag_id = self._create_tag_if_not_exists(conn, tag_name)
            
            # Link tag to object
            conn.execute("""
                INSERT OR IGNORE INTO object_tags (object_id, tag_id)
                VALUES (?, ?)
            """, (object_id, tag_id))
            
            # Update usage count
            conn.execute("""
                UPDATE tags SET usage_count = usage_count + 1 
                WHERE id = ?
            """, (tag_id,))
    
    def _create_tag_if_not_exists(self, conn, tag_name: str) -> str:
        """Create a tag if it doesn't exist and return its ID."""
        # Check if tag exists
        cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new tag
        tag_id = hashlib.md5(tag_name.encode()).hexdigest()[:16]
        conn.execute("""
            INSERT INTO tags (id, name) VALUES (?, ?)
        """, (tag_id, tag_name))
        
        return tag_id
    
    def _update_fts(self, conn, obj: SearchableObject):
        """Update full-text search index."""
        tags_text = " ".join(obj.tags) if obj.tags else ""
        conn.execute("""
            INSERT OR REPLACE INTO objects_fts (object_id, title, content, tags)
            VALUES (?, ?, ?, ?)
        """, (obj.id, obj.title, obj.content or "", tags_text))
    
    # Search Functionality
    def search(self, search_filter: SearchFilter) -> Dict[str, Any]:
        """Perform universal search with filters."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query parameters
                params = []
                where_conditions = []
                
                # Start with base query
                query = """
                    SELECT o.*, 
                           GROUP_CONCAT(t.name) as tag_names,
                           f.name as folder_name
                    FROM searchable_objects o
                    LEFT JOIN object_tags ot ON o.id = ot.object_id
                    LEFT JOIN tags t ON ot.tag_id = t.id
                    LEFT JOIN folders f ON o.folder_id = f.id
                """
                
                # Text search using FTS
                if search_filter.query.strip():
                    query += " INNER JOIN objects_fts fts ON o.id = fts.object_id"
                    where_conditions.append("objects_fts MATCH ?")
                    params.append(search_filter.query)
                
                # Object type filter
                if search_filter.object_types and len(search_filter.object_types) < len(ObjectType):
                    type_placeholders = ",".join(["?" for _ in search_filter.object_types])
                    where_conditions.append(f"o.type IN ({type_placeholders})")
                    params.extend([t.value for t in search_filter.object_types])
                
                # Boolean filters
                if search_filter.is_pinned is not None:
                    where_conditions.append("o.is_pinned = ?")
                    params.append(search_filter.is_pinned)
                
                if search_filter.is_shared is not None:
                    where_conditions.append("o.is_shared = ?")
                    params.append(search_filter.is_shared)
                
                if search_filter.is_archived is not None:
                    where_conditions.append("o.is_archived = ?")
                    params.append(search_filter.is_archived)
                
                # Author filter
                if search_filter.author:
                    where_conditions.append("o.author = ?")
                    params.append(search_filter.author)
                
                # Date filters
                if search_filter.date_from:
                    where_conditions.append("o.created_date >= ?")
                    params.append(search_filter.date_from.isoformat())
                
                if search_filter.date_to:
                    where_conditions.append("o.created_date <= ?")
                    params.append(search_filter.date_to.isoformat())
                
                # Folder filter
                if search_filter.folder_ids:
                    folder_placeholders = ",".join(["?" for _ in search_filter.folder_ids])
                    where_conditions.append(f"o.folder_id IN ({folder_placeholders})")
                    params.extend(search_filter.folder_ids)
                
                # Tag filter
                if search_filter.tags:
                    tag_placeholders = ",".join(["?" for _ in search_filter.tags])
                    where_conditions.append(f"""
                        o.id IN (
                            SELECT ot2.object_id FROM object_tags ot2
                            INNER JOIN tags t2 ON ot2.tag_id = t2.id
                            WHERE t2.name IN ({tag_placeholders})
                        )
                    """)
                    params.extend(search_filter.tags)
                
                # Add WHERE clause
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                # Add GROUP BY and ORDER BY
                query += " GROUP BY o.id ORDER BY o.modified_date DESC"
                
                # Get total count first (without LIMIT)
                count_query = f"SELECT COUNT(*) FROM ({query})"
                cursor = conn.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Add pagination
                query += " LIMIT ? OFFSET ?"
                params.extend([search_filter.limit, search_filter.offset])
                
                # Execute search
                cursor = conn.execute(query, params)
                results = cursor.fetchall()
                
                # Format results
                formatted_results = []
                for row in results:
                    obj_dict = dict(row)
                    obj_dict['metadata'] = json.loads(obj_dict['metadata']) if obj_dict['metadata'] else {}
                    obj_dict['tags'] = obj_dict['tag_names'].split(',') if obj_dict['tag_names'] else []
                    if 'tag_names' in obj_dict:
                        del obj_dict['tag_names']
                    formatted_results.append(obj_dict)
                
                return {
                    "results": formatted_results,
                    "total_count": total_count,
                    "page_size": search_filter.limit,
                    "offset": search_filter.offset,
                    "has_more": (search_filter.offset + len(formatted_results)) < total_count
                }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "results": [],
                "total_count": 0,
                "page_size": search_filter.limit,
                "offset": search_filter.offset,
                "has_more": False,
                "error": str(e)
            }
    
    # Folder Management
    def create_folder(self, folder: Folder) -> bool:
        """Create a new folder."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("""
                    INSERT INTO folders (id, name, parent_id, color, icon, object_types, created_date, is_shared)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    folder.id, folder.name, folder.parent_id, folder.color, folder.icon,
                    json.dumps([t.value for t in folder.object_types]),
                    folder.created_date.isoformat(),
                    folder.is_shared
                ))
                conn.commit()
                logger.info(f"Created folder: {folder.name}")
                return True
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return False
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders in hierarchical structure."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT f.*, COUNT(o.id) as object_count
                    FROM folders f
                    LEFT JOIN searchable_objects o ON f.id = o.folder_id
                    GROUP BY f.id
                    ORDER BY f.name
                """)
                
                folders = []
                for row in cursor.fetchall():
                    folder_dict = dict(row)
                    folder_dict['object_types'] = json.loads(folder_dict['object_types']) if folder_dict['object_types'] else []
                    folders.append(folder_dict)
                
                return folders
        except Exception as e:
            logger.error(f"Error getting folders: {e}")
            return []
    
    # Tag Management
    def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags sorted by usage count."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM tags 
                    ORDER BY usage_count DESC, name ASC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []
    
    def parse_smart_search(self, query: str) -> SearchFilter:
        """Parse smart search query with prefixes like 'pinned:true tag:important'."""
        search_filter = SearchFilter()
        
        # Extract and remove prefix filters
        parts = query.split()
        remaining_parts = []
        
        for part in parts:
            if ':' in part:
                prefix, value = part.split(':', 1)
                
                if prefix == 'pinned':
                    search_filter.is_pinned = value.lower() == 'true'
                elif prefix == 'shared':
                    search_filter.is_shared = value.lower() == 'true'
                elif prefix == 'archived':
                    search_filter.is_archived = value.lower() == 'true'
                elif prefix == 'type':
                    try:
                        search_filter.object_types = [ObjectType(value)]
                    except ValueError:
                        pass
                elif prefix == 'tag':
                    if search_filter.tags is None:
                        search_filter.tags = []
                    search_filter.tags.append(value)
                elif prefix == 'folder':
                    if search_filter.folder_ids is None:
                        search_filter.folder_ids = []
                    search_filter.folder_ids.append(value)
                elif prefix == 'author':
                    search_filter.author = value
                else:
                    remaining_parts.append(part)
            else:
                remaining_parts.append(part)
        
        # Set remaining text as general query
        search_filter.query = ' '.join(remaining_parts)
        
        return search_filter
    
    # Update and Delete Operations
    def update_object(self, obj: SearchableObject) -> bool:
        """Update an existing object."""
        obj.modified_date = datetime.now()
        return self.add_object(obj)  # INSERT OR REPLACE handles updates
    
    def delete_object(self, object_id: str) -> bool:
        """Delete an object and its associations."""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                # Delete from FTS
                conn.execute("DELETE FROM objects_fts WHERE object_id = ?", (object_id,))
                
                # Delete object (CASCADE will handle tags)
                conn.execute("DELETE FROM searchable_objects WHERE id = ?", (object_id,))
                
                conn.commit()
                logger.info(f"Deleted object: {object_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting object: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Initialize search system
    search_system = UniversalSearchSystem()
    
    # Add sample objects
    sample_objects = [
        SearchableObject(
            id="chat_001",
            type=ObjectType.CHAT,
            title="AI Discussion about Machine Learning",
            content="A detailed conversation about neural networks and deep learning.",
            tags=["ai", "machine-learning", "important"],
            is_pinned=True,
            author="user123"
        ),
        SearchableObject(
            id="doc_001",
            type=ObjectType.DOCUMENT,
            title="Project Requirements Document",
            content="Comprehensive requirements for the new AI assistant project.",
            tags=["project", "requirements", "ai"],
            folder_id="folder_work"
        ),
        SearchableObject(
            id="kb_001",
            type=ObjectType.KNOWLEDGE_BASE,
            title="ML Research Papers",
            content="Collection of research papers on machine learning algorithms.",
            tags=["research", "machine-learning", "papers"],
            is_shared=True
        )
    ]
    
    # Add sample folder
    work_folder = Folder(
        id="folder_work",
        name="Work Projects",
        color="#10B981",
        icon="briefcase"
    )
    
    search_system.create_folder(work_folder)
    
    # Add objects
    for obj in sample_objects:
        search_system.add_object(obj)
    
    # Test searches
    print("\n=== Test Search Results ===")
    
    # Basic search
    results = search_system.search(SearchFilter(query="machine learning"))
    print(f"Search 'machine learning': {len(results['results'])} results")
    
    # Smart search with prefixes
    smart_filter = search_system.parse_smart_search("pinned:true tag:ai")
    results = search_system.search(smart_filter)
    print(f"Smart search 'pinned:true tag:ai': {len(results['results'])} results")
    
    # Type filter
    results = search_system.search(SearchFilter(object_types=[ObjectType.DOCUMENT]))
    print(f"Document search: {len(results['results'])} results")
    
    # Get folders and tags
    folders = search_system.get_folders()
    tags = search_system.get_tags()
    print(f"Folders: {len(folders)}, Tags: {len(tags)}")
    
    print("Search system test completed successfully!")