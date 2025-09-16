# Phase 3 Graph Data Visualization Access Guide

## 🎯 Quick Answer

The Phase 3 graph data can be visualized in the web application at:

**Primary Access Points:**
- **Main Interface**: http://localhost:9090 (existing web app)
- **Dedicated Visualizations**: http://localhost:9090/visualizations.html
- **API Endpoints**: Direct JSON data access for custom integrations

## 📊 Available Visualizations

### 1. Knowledge Graph Visualization
**URL**: http://localhost:9090/visualizations.html (Knowledge Graph type)
**API**: `GET /api/visualizations/knowledge-graph`

- Interactive D3.js network graph
- Shows concepts, entities, and relationships
- Node sizes based on confidence scores
- Color-coded by entity type (CONCEPT, ENTITY, DOCUMENT)
- Drag and zoom interactions

### 2. Performance Dashboard
**URL**: http://localhost:9090/visualizations.html (Performance Dashboard type)
**API**: `GET /api/visualizations/performance`

- Real-time system metrics
- Query performance statistics
- Cache hit rates and success rates
- Multi-index system health monitoring

### 3. Search Results Explorer
**URL**: http://localhost:9090/visualizations.html (Search Explorer type)
**API**: `GET /api/visualizations/search-results`

- Document search results with relevance scores
- Interactive filtering and exploration
- Metadata display and source attribution

## 🌐 Web Application Integration

### Current Web App Structure (http://localhost:9090)
```
├── Chat Section (RAG-enhanced conversations)
├── Models Section (Ollama model management)
├── Knowledge Section (Document management)
├── Settings Section (Configuration)
└── [NEW] Visualizations Section (Phase 3 graphs)
```

### Access Methods

#### Method 1: Direct Visualization Page
```bash
# Open in browser
open http://localhost:9090/visualizations.html
```

#### Method 2: API Integration
```bash
# Knowledge Graph
curl http://localhost:9090/api/visualizations/knowledge-graph

# Performance Metrics
curl http://localhost:9090/api/visualizations/performance

# Search Results
curl http://localhost:9090/api/visualizations/search-results
```

#### Method 3: Programmatic Access
```python
import requests

# Get knowledge graph data
response = requests.get('http://localhost:9090/api/visualizations/knowledge-graph')
graph_data = response.json()

entities = graph_data['entities']
relationships = graph_data['relationships']
```

## 🔌 API Endpoints Reference

### Knowledge Graph API
**Endpoint**: `GET /api/visualizations/knowledge-graph`

**Response Structure**:
```json
{
  "entities": [
    {
      "id": "ai",
      "name": "Artificial Intelligence",
      "type": "CONCEPT",
      "confidence": 1.0
    }
  ],
  "relationships": [
    {
      "source": "ai",
      "target": "ml",
      "relationship": "INCLUDES",
      "weight": 0.9
    }
  ],
  "metadata": {
    "total_entities": 5,
    "total_relationships": 4,
    "generated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Performance Dashboard API
**Endpoint**: `GET /api/visualizations/performance`

**Response Structure**:
```json
{
  "metrics": {
    "total_queries": 1247,
    "avg_query_time": 0.28,
    "success_rate": 0.987,
    "cache_hit_rate": 0.73,
    "active_indices": ["vector", "metadata", "fts"],
    "system_health": "healthy"
  },
  "time_series": [...],
  "alerts": [],
  "recommendations": [...]
}
```

### Search Results API
**Endpoint**: `GET /api/visualizations/search-results`

**Response Structure**:
```json
{
  "search_results": [
    {
      "id": "doc1",
      "title": "Machine Learning Fundamentals",
      "content": "Comprehensive guide...",
      "score": 0.95,
      "source": "ml_guide.pdf",
      "metadata": {...}
    }
  ],
  "query_info": {
    "query": "machine learning",
    "total_found": 3,
    "execution_time": 0.125,
    "strategy": "hybrid"
  }
}
```

## 🛠️ Development and Customization

### File Locations
- **Visualization Page**: `/home/junior/src/red/visualizations.html`
- **Server API Handlers**: `/home/junior/src/red/server.py` (lines 770-906)
- **Demo Script**: `/home/junior/src/red/visualization_demo.py`

### Customizing Visualizations
1. **Modify D3.js Components**: Edit `visualizations.html`
2. **Extend API Data**: Modify server handlers in `server.py`
3. **Add New Visualization Types**: Extend the visualization renderer

### Testing Visualizations
```bash
# Run demo script
uv run visualization_demo.py

# Test specific endpoints
curl http://localhost:9090/api/visualizations/knowledge-graph | jq
curl http://localhost:9090/api/visualizations/performance | jq
curl http://localhost:9090/api/visualizations/search-results | jq
```

## 🎨 Visualization Features

### Interactive Knowledge Graphs
- **Technology**: D3.js force-directed graph
- **Features**:
  - Drag nodes to reposition
  - Zoom and pan interactions
  - Hover tooltips
  - Color-coded entity types
  - Relationship strength visualization

### Performance Dashboards
- **Technology**: HTML/CSS grid with dynamic updates
- **Metrics Displayed**:
  - Total queries processed
  - Average response time
  - Success rate percentage
  - Cache hit rate
  - System health status

### Search Result Explorers
- **Technology**: Responsive HTML with relevance scoring
- **Features**:
  - Document cards with metadata
  - Relevance score visualization
  - Source file attribution
  - Content previews

## 🔗 Integration with Phase 3 Components

The visualizations integrate with all Phase 3 systems:

1. **Enhanced Query Executor** → Performance metrics
2. **Intelligent Query Planner** → Strategy visualization
3. **Advanced Redis Caching** → Cache performance data
4. **Real-time Collaboration** → Shared workspace analytics
5. **MCP Integration** → AI agent interaction data
6. **Production Monitoring** → System health metrics

## 📈 Usage Examples

### View Knowledge Relationships
1. Open http://localhost:9090/visualizations.html
2. Select "Knowledge Graph" from dropdown
3. Click "Refresh Visualization"
4. Interact with the network graph

### Monitor System Performance
1. Select "Performance Dashboard"
2. View real-time metrics
3. Check system health indicators

### Explore Search Results
1. Select "Search Results Explorer"
2. Browse document relevance scores
3. Examine search execution data

## 🎯 Quick Start

1. **Ensure server is running**: `uv run server.py`
2. **Open browser**: Navigate to http://localhost:9090/visualizations.html
3. **Select visualization type**: Choose from dropdown menu
4. **Interact**: Explore the interactive visualizations

The Phase 3 visualization system is now fully integrated and accessible through the existing web application infrastructure!