"""
Observable D3 Visualization Components for Phase 3

Provides interactive visualization components for exploring multi-index
query results, performance metrics, and knowledge graphs.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class D3VisualizationEngine:
    """
    Engine for generating Observable D3 visualization components.

    Creates interactive visualizations for:
    - Knowledge graphs and entity relationships
    - Query performance dashboards
    - Search result exploration
    - Index health monitoring
    - Real-time analytics
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.visualization_templates = {}
        self.generated_visualizations = {}

        # Load visualization templates
        self._load_visualization_templates()

    def _load_visualization_templates(self):
        """Load D3 visualization templates."""
        self.visualization_templates = {
            "knowledge_graph": {
                "type": "force_directed_graph",
                "description": "Interactive knowledge graph with entity relationships",
                "features": ["zoom", "drag", "hover_details", "filtering"]
            },
            "performance_dashboard": {
                "type": "multi_chart_dashboard",
                "description": "Real-time performance monitoring dashboard",
                "features": ["time_series", "bar_charts", "gauges", "alerts"]
            },
            "search_results": {
                "type": "enhanced_list_view",
                "description": "Interactive search results with relevance visualization",
                "features": ["sorting", "filtering", "grouping", "detail_view"]
            },
            "index_health": {
                "type": "status_grid",
                "description": "Index health and status monitoring",
                "features": ["status_indicators", "metrics_overlay", "drill_down"]
            },
            "query_analytics": {
                "type": "analytics_charts",
                "description": "Query pattern and performance analytics",
                "features": ["trend_analysis", "pattern_detection", "outlier_highlighting"]
            }
        }

    def create_knowledge_graph(self, entities: List[Dict[str, Any]],
                              relationships: List[Dict[str, Any]],
                              config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create interactive knowledge graph visualization."""
        viz_id = f"knowledge_graph_{uuid.uuid4().hex[:8]}"

        # Process entities and relationships for D3
        nodes = []
        links = []

        # Convert entities to nodes
        entity_map = {}
        for i, entity in enumerate(entities):
            node = {
                "id": entity.get("id", f"entity_{i}"),
                "name": entity.get("name", entity.get("entity", f"Entity {i}")),
                "type": entity.get("type", "UNKNOWN"),
                "confidence": entity.get("confidence", 1.0),
                "properties": entity.get("properties", {}),
                "group": self._get_entity_group(entity.get("type", "UNKNOWN"))
            }
            nodes.append(node)
            entity_map[node["id"]] = node

        # Convert relationships to links
        for relationship in relationships:
            source_id = relationship.get("source", relationship.get("from"))
            target_id = relationship.get("target", relationship.get("to"))

            if source_id in entity_map and target_id in entity_map:
                link = {
                    "source": source_id,
                    "target": target_id,
                    "relationship": relationship.get("relationship", relationship.get("type", "RELATED")),
                    "weight": relationship.get("weight", relationship.get("confidence", 1.0)),
                    "properties": relationship.get("properties", {})
                }
                links.append(link)

        # Generate D3 configuration
        d3_config = {
            "id": viz_id,
            "type": "force_directed_graph",
            "data": {
                "nodes": nodes,
                "links": links
            },
            "config": {
                "width": config.get("width", 800) if config else 800,
                "height": config.get("height", 600) if config else 600,
                "node_radius": config.get("node_radius", 8) if config else 8,
                "link_distance": config.get("link_distance", 50) if config else 50,
                "charge_strength": config.get("charge_strength", -200) if config else -200,
                "color_scheme": config.get("color_scheme", "category10") if config else "category10"
            },
            "interactions": {
                "drag": True,
                "zoom": True,
                "hover": True,
                "click": True
            },
            "features": {
                "search": True,
                "filter": True,
                "export": True,
                "fullscreen": True
            }
        }

        # Generate Observable notebook code
        observable_code = self._generate_knowledge_graph_code(d3_config)

        visualization = {
            "id": viz_id,
            "title": "Knowledge Graph Visualization",
            "type": "knowledge_graph",
            "d3_config": d3_config,
            "observable_code": observable_code,
            "created_at": datetime.now().isoformat(),
            "stats": {
                "node_count": len(nodes),
                "link_count": len(links),
                "entity_types": len(set(node["type"] for node in nodes))
            }
        }

        self.generated_visualizations[viz_id] = visualization
        return visualization

    def create_performance_dashboard(self, metrics: Dict[str, Any],
                                   time_series_data: List[Dict[str, Any]],
                                   config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create performance monitoring dashboard."""
        viz_id = f"performance_dashboard_{uuid.uuid4().hex[:8]}"

        # Process metrics for visualization
        dashboard_data = {
            "summary_metrics": self._process_summary_metrics(metrics),
            "time_series": self._process_time_series_data(time_series_data),
            "performance_breakdown": self._process_performance_breakdown(metrics),
            "alerts": self._generate_performance_alerts(metrics)
        }

        # Generate D3 configuration
        d3_config = {
            "id": viz_id,
            "type": "performance_dashboard",
            "data": dashboard_data,
            "layout": {
                "grid_cols": config.get("grid_cols", 3) if config else 3,
                "chart_height": config.get("chart_height", 200) if config else 200,
                "refresh_interval": config.get("refresh_interval", 5000) if config else 5000
            },
            "charts": [
                {
                    "type": "gauge",
                    "title": "Query Performance",
                    "metric": "avg_query_time",
                    "max_value": 10.0,
                    "thresholds": [3.0, 7.0]
                },
                {
                    "type": "line_chart",
                    "title": "Queries Per Second",
                    "data_key": "query_rate_timeline",
                    "y_axis": "Queries/sec"
                },
                {
                    "type": "bar_chart",
                    "title": "Index Utilization",
                    "data_key": "index_usage",
                    "x_axis": "Index",
                    "y_axis": "Usage %"
                },
                {
                    "type": "heatmap",
                    "title": "Performance Matrix",
                    "data_key": "performance_matrix",
                    "color_scale": "interpolateRdYlGn"
                }
            ]
        }

        # Generate Observable notebook code
        observable_code = self._generate_dashboard_code(d3_config)

        visualization = {
            "id": viz_id,
            "title": "Performance Dashboard",
            "type": "performance_dashboard",
            "d3_config": d3_config,
            "observable_code": observable_code,
            "created_at": datetime.now().isoformat(),
            "auto_refresh": True,
            "stats": {
                "chart_count": len(d3_config["charts"]),
                "metric_count": len(dashboard_data["summary_metrics"]),
                "time_range": self._get_time_range(time_series_data)
            }
        }

        self.generated_visualizations[viz_id] = visualization
        return visualization

    def create_search_results_explorer(self, search_results: List[Dict[str, Any]],
                                     query_info: Dict[str, Any],
                                     config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create interactive search results explorer."""
        viz_id = f"search_explorer_{uuid.uuid4().hex[:8]}"

        # Process search results for visualization
        processed_results = []
        for i, result in enumerate(search_results):
            processed_result = {
                "id": result.get("id", f"result_{i}"),
                "title": result.get("title", "Untitled"),
                "content": result.get("content", result.get("description", ""))[:200] + "...",
                "score": result.get("score", result.get("relevance_score", 0)),
                "source": result.get("source", result.get("index_used", "unknown")),
                "timestamp": result.get("created_at", result.get("timestamp", "")),
                "metadata": result.get("metadata", {}),
                "relevance_factors": self._analyze_relevance_factors(result, query_info)
            }
            processed_results.append(processed_result)

        # Generate D3 configuration
        d3_config = {
            "id": viz_id,
            "type": "search_results_explorer",
            "data": {
                "results": processed_results,
                "query_info": query_info,
                "facets": self._extract_facets(processed_results),
                "relevance_distribution": self._calculate_relevance_distribution(processed_results)
            },
            "layout": {
                "view_mode": config.get("view_mode", "list") if config else "list",
                "items_per_page": config.get("items_per_page", 10) if config else 10,
                "show_relevance_viz": config.get("show_relevance_viz", True) if config else True
            },
            "features": {
                "sorting": ["relevance", "date", "title", "source"],
                "filtering": ["source", "date_range", "score_range"],
                "grouping": ["source", "date", "topic"],
                "export": ["json", "csv", "pdf"]
            }
        }

        # Generate Observable notebook code
        observable_code = self._generate_search_explorer_code(d3_config)

        visualization = {
            "id": viz_id,
            "title": f"Search Results: {query_info.get('query', 'Unknown Query')}",
            "type": "search_results_explorer",
            "d3_config": d3_config,
            "observable_code": observable_code,
            "created_at": datetime.now().isoformat(),
            "stats": {
                "result_count": len(processed_results),
                "source_count": len(set(r["source"] for r in processed_results)),
                "avg_relevance": sum(r["score"] for r in processed_results) / max(len(processed_results), 1)
            }
        }

        self.generated_visualizations[viz_id] = visualization
        return visualization

    def create_index_health_monitor(self, index_status: Dict[str, Any],
                                   performance_metrics: Dict[str, Any],
                                   config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create index health monitoring visualization."""
        viz_id = f"index_health_{uuid.uuid4().hex[:8]}"

        # Process index data
        index_data = []
        for index_name, status_info in index_status.items():
            index_metrics = performance_metrics.get(index_name, {})

            index_data.append({
                "name": index_name,
                "status": status_info.get("status", "unknown"),
                "health_score": self._calculate_health_score(status_info, index_metrics),
                "metrics": {
                    "query_count": index_metrics.get("query_count", 0),
                    "avg_response_time": index_metrics.get("avg_response_time", 0),
                    "error_rate": index_metrics.get("error_rate", 0),
                    "storage_size": index_metrics.get("storage_size", 0)
                },
                "capabilities": status_info.get("capabilities", []),
                "last_updated": status_info.get("last_updated", ""),
                "alerts": self._generate_index_alerts(status_info, index_metrics)
            })

        # Generate D3 configuration
        d3_config = {
            "id": viz_id,
            "type": "index_health_monitor",
            "data": {
                "indices": index_data,
                "overall_health": self._calculate_overall_health(index_data),
                "health_trends": self._generate_health_trends(index_data)
            },
            "layout": {
                "grid_view": config.get("grid_view", True) if config else True,
                "show_metrics": config.get("show_metrics", True) if config else True,
                "alert_threshold": config.get("alert_threshold", 0.7) if config else 0.7
            },
            "visualizations": {
                "status_indicators": True,
                "health_sparklines": True,
                "metric_charts": True,
                "alert_panel": True
            }
        }

        # Generate Observable notebook code
        observable_code = self._generate_health_monitor_code(d3_config)

        visualization = {
            "id": viz_id,
            "title": "Index Health Monitor",
            "type": "index_health_monitor",
            "d3_config": d3_config,
            "observable_code": observable_code,
            "created_at": datetime.now().isoformat(),
            "auto_refresh": True,
            "stats": {
                "index_count": len(index_data),
                "healthy_indices": len([idx for idx in index_data if idx["health_score"] > 0.8]),
                "total_alerts": sum(len(idx["alerts"]) for idx in index_data)
            }
        }

        self.generated_visualizations[viz_id] = visualization
        return visualization

    def generate_observable_notebook(self, visualization_id: str) -> str:
        """Generate complete Observable notebook for a visualization."""
        if visualization_id not in self.generated_visualizations:
            raise ValueError(f"Visualization {visualization_id} not found")

        viz = self.generated_visualizations[visualization_id]

        notebook_content = f"""
// {viz['title']}
// Generated by Multi-Index System - Phase 3
// Created: {viz['created_at']}

// Import D3 and other dependencies
import {{d3}} from "d3@7"
import {{DOM}} from "stdlib"

// Visualization configuration
const config = {json.dumps(viz['d3_config'], indent=2)}

// Main visualization function
{viz['observable_code']}

// Export the visualization
export default function define(runtime, observer) {{
  const main = runtime.module();

  main.variable(observer("chart")).define("chart", ["d3", "DOM"], function(d3, DOM) {{
    return create{viz['type'].replace('_', '').title()}(config);
  }});

  return main;
}}
"""
        return notebook_content

    def export_all_visualizations(self, output_dir: str) -> Dict[str, str]:
        """Export all visualizations as Observable notebooks."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files = {}

        for viz_id, viz in self.generated_visualizations.items():
            notebook_content = self.generate_observable_notebook(viz_id)

            filename = f"{viz['type']}_{viz_id}.js"
            file_path = output_path / filename

            with open(file_path, 'w') as f:
                f.write(notebook_content)

            exported_files[viz_id] = str(file_path)

        return exported_files

    # Helper methods for data processing

    def _get_entity_group(self, entity_type: str) -> int:
        """Get group number for entity type for visualization coloring."""
        type_groups = {
            "PERSON": 1,
            "ORGANIZATION": 2,
            "LOCATION": 3,
            "CONCEPT": 4,
            "EVENT": 5,
            "PRODUCT": 6,
            "DOCUMENT": 7
        }
        return type_groups.get(entity_type, 0)

    def _process_summary_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Process metrics for dashboard summary."""
        return {
            "total_queries": metrics.get("total_queries", 0),
            "avg_query_time": metrics.get("avg_query_time", 0),
            "success_rate": metrics.get("success_rate", 1.0),
            "cache_hit_rate": metrics.get("cache_hit_rate", 0),
            "active_indices": metrics.get("active_indices", 0),
            "data_volume": metrics.get("data_volume", 0)
        }

    def _process_time_series_data(self, time_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process time series data for charts."""
        processed = []
        for point in time_series:
            processed.append({
                "timestamp": point.get("timestamp", ""),
                "query_count": point.get("query_count", 0),
                "avg_response_time": point.get("avg_response_time", 0),
                "error_count": point.get("error_count", 0),
                "cache_hits": point.get("cache_hits", 0)
            })
        return processed

    def _process_performance_breakdown(self, metrics: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Process performance breakdown data."""
        return {
            "by_index": [
                {"name": name, "value": data.get("avg_time", 0)}
                for name, data in metrics.get("index_performance", {}).items()
            ],
            "by_query_type": [
                {"name": qtype, "value": data.get("avg_time", 0)}
                for qtype, data in metrics.get("query_type_performance", {}).items()
            ]
        }

    def _generate_performance_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance alerts based on metrics."""
        alerts = []

        avg_time = metrics.get("avg_query_time", 0)
        if avg_time > 5.0:
            alerts.append({
                "type": "warning",
                "message": f"High average query time: {avg_time:.2f}s",
                "severity": "medium"
            })

        success_rate = metrics.get("success_rate", 1.0)
        if success_rate < 0.95:
            alerts.append({
                "type": "error",
                "message": f"Low success rate: {success_rate:.1%}",
                "severity": "high"
            })

        return alerts

    def _analyze_relevance_factors(self, result: Dict[str, Any], query_info: Dict[str, Any]) -> List[str]:
        """Analyze what makes a result relevant."""
        factors = []

        query_terms = query_info.get("query", "").lower().split()
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()

        # Check for title matches
        title_matches = [term for term in query_terms if term in title]
        if title_matches:
            factors.append(f"Title matches: {', '.join(title_matches)}")

        # Check for content matches
        content_matches = [term for term in query_terms if term in content]
        if content_matches:
            factors.append(f"Content matches: {', '.join(content_matches)}")

        # Check scores
        if result.get("score", 0) > 0.8:
            factors.append("High similarity score")

        return factors

    def _extract_facets(self, results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract facets for filtering."""
        facets = {
            "sources": list(set(r["source"] for r in results)),
            "score_ranges": ["0-0.3", "0.3-0.6", "0.6-0.8", "0.8-1.0"],
            "date_ranges": self._extract_date_ranges(results)
        }
        return facets

    def _extract_date_ranges(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract date ranges from results."""
        # Simple date range extraction
        return ["Last 24 hours", "Last week", "Last month", "Last year", "All time"]

    def _calculate_relevance_distribution(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate relevance score distribution."""
        buckets = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        distribution = []

        for i in range(len(buckets) - 1):
            count = len([r for r in results if buckets[i] <= r["score"] < buckets[i+1]])
            distribution.append({
                "range": f"{buckets[i]:.1f}-{buckets[i+1]:.1f}",
                "count": count
            })

        return distribution

    def _calculate_health_score(self, status_info: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """Calculate overall health score for an index."""
        score = 1.0

        # Status penalty
        status = status_info.get("status", "unknown")
        if status == "degraded":
            score *= 0.7
        elif status == "unhealthy":
            score *= 0.3
        elif status == "unknown":
            score *= 0.5

        # Performance penalty
        avg_time = metrics.get("avg_response_time", 0)
        if avg_time > 2.0:
            score *= 0.8
        elif avg_time > 5.0:
            score *= 0.6

        # Error rate penalty
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 0.1:
            score *= 0.7
        elif error_rate > 0.05:
            score *= 0.9

        return max(0.0, min(1.0, score))

    def _calculate_overall_health(self, index_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall system health."""
        if not index_data:
            return {"score": 0.0, "status": "unknown"}

        avg_health = sum(idx["health_score"] for idx in index_data) / len(index_data)

        if avg_health > 0.9:
            status = "excellent"
        elif avg_health > 0.7:
            status = "good"
        elif avg_health > 0.5:
            status = "degraded"
        else:
            status = "critical"

        return {
            "score": avg_health,
            "status": status,
            "healthy_count": len([idx for idx in index_data if idx["health_score"] > 0.8]),
            "total_count": len(index_data)
        }

    def _generate_health_trends(self, index_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate health trend data."""
        # Mock trend data - in real implementation would use historical data
        return [
            {"timestamp": "2024-01-01T00:00:00Z", "health_score": 0.95},
            {"timestamp": "2024-01-01T01:00:00Z", "health_score": 0.92},
            {"timestamp": "2024-01-01T02:00:00Z", "health_score": 0.88},
            {"timestamp": "2024-01-01T03:00:00Z", "health_score": 0.90}
        ]

    def _generate_index_alerts(self, status_info: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts for an index."""
        alerts = []

        if status_info.get("status") == "degraded":
            alerts.append({
                "type": "warning",
                "message": "Index performance degraded",
                "timestamp": datetime.now().isoformat()
            })

        if metrics.get("error_rate", 0) > 0.1:
            alerts.append({
                "type": "error",
                "message": f"High error rate: {metrics['error_rate']:.1%}",
                "timestamp": datetime.now().isoformat()
            })

        return alerts

    def _get_time_range(self, time_series: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get time range from time series data."""
        if not time_series:
            return {"start": "", "end": ""}

        timestamps = [point.get("timestamp", "") for point in time_series if point.get("timestamp")]

        return {
            "start": min(timestamps) if timestamps else "",
            "end": max(timestamps) if timestamps else ""
        }

    # Code generation methods

    def _generate_knowledge_graph_code(self, config: Dict[str, Any]) -> str:
        """Generate Observable D3 code for knowledge graph."""
        return f"""
function createKnowledgeGraph(config) {{
    const width = config.config.width;
    const height = config.config.height;

    const svg = d3.create("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height]);

    const simulation = d3.forceSimulation(config.data.nodes)
        .force("link", d3.forceLink(config.data.links).id(d => d.id).distance({config['config']['link_distance']}))
        .force("charge", d3.forceManyBody().strength({config['config']['charge_strength']}))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(config.data.links)
        .join("line")
        .attr("stroke-width", d => Math.sqrt(d.weight * 3));

    const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(config.data.nodes)
        .join("circle")
        .attr("r", {config['config']['node_radius']})
        .attr("fill", d => d3.schemeCategory10[d.group])
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("title")
        .text(d => `${{d.name}} (${{d.type}})`);

    simulation.on("tick", () => {{
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
    }});

    function dragstarted(event, d) {{
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }}

    function dragged(event, d) {{
        d.fx = event.x;
        d.fy = event.y;
    }}

    function dragended(event, d) {{
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }}

    return svg.node();
}}
"""

    def _generate_dashboard_code(self, config: Dict[str, Any]) -> str:
        """Generate Observable D3 code for performance dashboard."""
        return f"""
function createPerformanceDashboard(config) {{
    const container = d3.create("div")
        .style("display", "grid")
        .style("grid-template-columns", "repeat({config['layout']['grid_cols']}, 1fr)")
        .style("gap", "20px")
        .style("padding", "20px");

    // Create each chart
    config.charts.forEach(chartConfig => {{
        const chartDiv = container.append("div")
            .style("border", "1px solid #ddd")
            .style("border-radius", "8px")
            .style("padding", "15px")
            .style("background", "white");

        chartDiv.append("h3")
            .text(chartConfig.title)
            .style("margin-top", "0");

        if (chartConfig.type === "gauge") {{
            createGauge(chartDiv, chartConfig, config.data);
        }} else if (chartConfig.type === "line_chart") {{
            createLineChart(chartDiv, chartConfig, config.data);
        }} else if (chartConfig.type === "bar_chart") {{
            createBarChart(chartDiv, chartConfig, config.data);
        }} else if (chartConfig.type === "heatmap") {{
            createHeatmap(chartDiv, chartConfig, config.data);
        }}
    }});

    return container.node();
}}

function createGauge(container, chartConfig, data) {{
    const width = 200;
    const height = 150;
    const radius = Math.min(width, height) / 2 - 20;

    const svg = container.append("svg")
        .attr("width", width)
        .attr("height", height);

    const g = svg.append("g")
        .attr("transform", `translate(${{width/2}},${{height/2}})`);

    const value = data.summary_metrics[chartConfig.metric] || 0;
    const maxValue = chartConfig.max_value;
    const angle = (value / maxValue) * Math.PI;

    // Background arc
    g.append("path")
        .datum({{startAngle: -Math.PI/2, endAngle: Math.PI/2}})
        .style("fill", "#f0f0f0")
        .attr("d", d3.arc().innerRadius(radius-20).outerRadius(radius));

    // Value arc
    g.append("path")
        .datum({{startAngle: -Math.PI/2, endAngle: -Math.PI/2 + angle}})
        .style("fill", value > chartConfig.thresholds[1] ? "#ff4444" :
                       value > chartConfig.thresholds[0] ? "#ffaa00" : "#44ff44")
        .attr("d", d3.arc().innerRadius(radius-20).outerRadius(radius));

    // Value text
    g.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .style("font-size", "18px")
        .style("font-weight", "bold")
        .text(value.toFixed(2));
}}
"""

    def _generate_search_explorer_code(self, config: Dict[str, Any]) -> str:
        """Generate Observable D3 code for search results explorer."""
        return f"""
function createSearchResultsExplorer(config) {{
    const container = d3.create("div")
        .style("max-width", "1200px")
        .style("margin", "0 auto");

    // Header with search info
    const header = container.append("div")
        .style("background", "#f8f9fa")
        .style("padding", "20px")
        .style("border-radius", "8px")
        .style("margin-bottom", "20px");

    header.append("h2")
        .text(`Search Results: "${{config.data.query_info.query}}"`);

    header.append("p")
        .text(`Found ${{config.data.results.length}} results`);

    // Filters section
    const filters = container.append("div")
        .style("display", "flex")
        .style("gap", "15px")
        .style("margin-bottom", "20px");

    // Source filter
    const sourceFilter = filters.append("select")
        .style("padding", "8px")
        .on("change", function() {{
            filterResults(this.value, "source");
        }});

    sourceFilter.append("option").attr("value", "").text("All Sources");
    config.data.facets.sources.forEach(source => {{
        sourceFilter.append("option").attr("value", source).text(source);
    }});

    // Results container
    const resultsContainer = container.append("div")
        .attr("id", "results-container");

    renderResults(config.data.results);

    function renderResults(results) {{
        const resultDivs = resultsContainer.selectAll(".result")
            .data(results)
            .join("div")
            .attr("class", "result")
            .style("border", "1px solid #ddd")
            .style("border-radius", "8px")
            .style("padding", "15px")
            .style("margin-bottom", "10px")
            .style("background", "white");

        resultDivs.append("h3")
            .style("margin-top", "0")
            .style("color", "#0066cc")
            .text(d => d.title);

        resultDivs.append("p")
            .style("color", "#666")
            .text(d => d.content);

        resultDivs.append("div")
            .style("display", "flex")
            .style("justify-content", "space-between")
            .style("margin-top", "10px")
            .style("font-size", "12px")
            .style("color", "#888")
            .html(d => `
                <span>Source: ${{d.source}}</span>
                <span>Relevance: ${{(d.score * 100).toFixed(1)}}%</span>
            `);
    }}

    function filterResults(value, type) {{
        let filtered = config.data.results;
        if (value && type === "source") {{
            filtered = filtered.filter(d => d.source === value);
        }}
        renderResults(filtered);
    }}

    return container.node();
}}
"""

    def _generate_health_monitor_code(self, config: Dict[str, Any]) -> str:
        """Generate Observable D3 code for index health monitor."""
        return f"""
function createIndexHealthMonitor(config) {{
    const container = d3.create("div")
        .style("padding", "20px");

    // Overall health summary
    const summary = container.append("div")
        .style("background", getHealthColor(config.data.overall_health.score))
        .style("color", "white")
        .style("padding", "20px")
        .style("border-radius", "8px")
        .style("margin-bottom", "20px")
        .style("text-align", "center");

    summary.append("h2")
        .text("System Health")
        .style("margin", "0");

    summary.append("div")
        .style("font-size", "24px")
        .style("margin", "10px 0")
        .text(`${{(config.data.overall_health.score * 100).toFixed(1)}}%`);

    summary.append("div")
        .text(`${{config.data.overall_health.healthy_count}} of ${{config.data.overall_health.total_count}} indices healthy`);

    // Index grid
    const grid = container.append("div")
        .style("display", "grid")
        .style("grid-template-columns", "repeat(auto-fit, minmax(300px, 1fr))")
        .style("gap", "20px");

    const indexCards = grid.selectAll(".index-card")
        .data(config.data.indices)
        .join("div")
        .attr("class", "index-card")
        .style("border", "1px solid #ddd")
        .style("border-radius", "8px")
        .style("padding", "15px")
        .style("background", "white");

    // Index headers
    const headers = indexCards.append("div")
        .style("display", "flex")
        .style("justify-content", "space-between")
        .style("align-items", "center")
        .style("margin-bottom", "15px");

    headers.append("h3")
        .style("margin", "0")
        .text(d => d.name);

    headers.append("div")
        .style("width", "20px")
        .style("height", "20px")
        .style("border-radius", "50%")
        .style("background", d => getHealthColor(d.health_score));

    // Metrics
    indexCards.append("div")
        .style("font-size", "14px")
        .style("color", "#666")
        .html(d => `
            <div>Health Score: ${{(d.health_score * 100).toFixed(1)}}%</div>
            <div>Queries: ${{d.metrics.query_count}}</div>
            <div>Avg Response: ${{d.metrics.avg_response_time.toFixed(3)}}s</div>
            <div>Error Rate: ${{(d.metrics.error_rate * 100).toFixed(1)}}%</div>
        `);

    // Alerts
    indexCards.filter(d => d.alerts.length > 0)
        .append("div")
        .style("margin-top", "10px")
        .style("padding", "8px")
        .style("background", "#fff3cd")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .text(d => `${{d.alerts.length}} alert(s)`);

    function getHealthColor(score) {{
        if (score > 0.9) return "#28a745";
        if (score > 0.7) return "#ffc107";
        if (score > 0.5) return "#fd7e14";
        return "#dc3545";
    }}

    return container.node();
}}
"""