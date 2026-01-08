"""
Ollama Agent Runtime with Skills Support.

This module provides:
- COST-FIRST: Zero-cost local Ollama agent execution
- AGENT-NATIVE: Skills-based agent capabilities
- LOCAL-FIRST: Complete localhost operation
- SIMPLE-SCALE: Optimized for 5 concurrent users
"""

import json
import logging
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests

# Configure logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import path utilities
from project_paths import get_project_root, resolve_path

# Import web tools for agent function calling
try:
    from agent_system.web_tools import web_search, web_fetch, search_faculty_hires, extract_faculty_profile
    WEB_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Web tools not available: {e}")
    WEB_TOOLS_AVAILABLE = False

# Import shredding tools for agent function calling
try:
    from agent_system.shredding_tools import shred_rfp, get_opportunity_status, shred_directory
    SHREDDING_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Shredding tools not available: {e}")
    SHREDDING_TOOLS_AVAILABLE = False


@dataclass
class AgentSkill:
    """Represents a skill that an agent can use."""
    name: str
    description: str
    skill_path: Path
    metadata: Dict[str, Any]
    source: str = "local"  # "local" or "plugin"


@dataclass
class OllamaAgentConfig:
    """Configuration for an Ollama agent."""
    agent_id: str
    name: str
    description: str
    model: str = "qwen2.5:3b"  # Default zero-cost local model
    capabilities: List[str] = None
    skills: List[str] = None  # List of skill names
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: Optional[str] = None
    status: str = "active"  # "active" or "inactive"


class OllamaAgentRuntime:
    """
    Runtime for executing agents with local Ollama models and skills.

    This runtime provides:
    - Zero-cost local LLM execution via Ollama
    - Skills-based agent capabilities
    - Agent lifecycle management
    - Skills loading and invocation
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Initialize Ollama agent runtime.

        Args:
            ollama_url: URL of local Ollama server (default: localhost:11434)
        """
        self.ollama_url = ollama_url
        self.active_agents: Dict[str, OllamaAgentConfig] = {}
        self.skills_cache: Dict[str, AgentSkill] = {}
        self.skills_dir = get_project_root() / ".claude" / "skills"
        self.plugin_skills_dir = Path.home() / ".claude" / "plugins" / "cache" / "anthropic-agent-skills" / "document-skills"
        self.agents_config_file = get_project_root() / "agent_system" / "agents_config.json"

        # Ensure directories exist
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.agents_config_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tool registry for agent function calling
        self._init_tool_registry()

        # Load available skills from both sources
        self._load_skills()
        self._load_plugin_skills()

        local_count = sum(1 for s in self.skills_cache.values() if s.source == "local")
        plugin_count = sum(1 for s in self.skills_cache.values() if s.source == "plugin")

        logger.info(f"✅ Ollama Agent Runtime initialized (URL: {ollama_url})")
        logger.info(f"✅ Loaded {local_count} local skills from {self.skills_dir}")
        logger.info(f"✅ Loaded {plugin_count} plugin skills from Anthropic plugins")

        # Load agents from persistent storage
        self._load_agents_from_file()

        # Create default agents if none exist
        if len(self.active_agents) == 0:
            self._create_default_agents()

    def _load_skills(self):
        """Load all available skills from .claude/skills directory."""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                logger.warning(f"Skill directory {skill_dir.name} missing SKILL.md")
                continue

            try:
                skill = self._parse_skill(skill_dir, skill_md, source="local")
                self.skills_cache[skill.name] = skill
                logger.info(f"  ✅ Loaded local skill: {skill.name}")
            except Exception as e:
                logger.error(f"  ❌ Failed to load skill {skill_dir.name}: {e}")

    def _load_plugin_skills(self):
        """Load all available skills from plugin directories."""
        if not self.plugin_skills_dir.exists():
            logger.info(f"Plugin skills directory not found: {self.plugin_skills_dir}")
            return

        # Find the skills subdirectory (there may be version directories)
        for version_dir in self.plugin_skills_dir.iterdir():
            if not version_dir.is_dir():
                continue

            skills_dir = version_dir / "skills"
            if not skills_dir.exists():
                continue

            logger.info(f"Loading plugin skills from: {skills_dir}")

            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    logger.warning(f"Plugin skill directory {skill_dir.name} missing SKILL.md")
                    continue

                try:
                    skill = self._parse_skill(skill_dir, skill_md, source="plugin")
                    self.skills_cache[skill.name] = skill
                    logger.info(f"  ✅ Loaded plugin skill: {skill.name}")
                except Exception as e:
                    logger.error(f"  ❌ Failed to load plugin skill {skill_dir.name}: {e}")

    def _parse_skill(self, skill_dir: Path, skill_md: Path, source: str = "local") -> AgentSkill:
        """
        Parse a skill from its SKILL.md file.

        Args:
            skill_dir: Directory containing the skill
            skill_md: Path to SKILL.md file
            source: Source of the skill ("local" or "plugin")

        Returns:
            AgentSkill object
        """
        with open(skill_md, 'r') as f:
            content = f.read()

        # Parse YAML frontmatter
        if not content.startswith('---'):
            raise ValueError("SKILL.md must start with YAML frontmatter")

        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError("Invalid SKILL.md format")

        # Parse YAML frontmatter (simple parser for name and description)
        frontmatter = parts[1].strip()
        metadata = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        if 'name' not in metadata or 'description' not in metadata:
            raise ValueError("SKILL.md must have 'name' and 'description' in frontmatter")

        return AgentSkill(
            name=metadata['name'],
            description=metadata['description'],
            skill_path=skill_dir,
            metadata=metadata,
            source=source
        )

    def list_skills(self) -> List[Dict[str, Any]]:
        """
        List all available skills.

        Returns:
            List of skill metadata dictionaries
        """
        return [
            {
                'name': skill.name,
                'description': skill.description,
                'path': str(skill.skill_path),
                'source': skill.source
            }
            for skill in self.skills_cache.values()
        ]

    def get_skill(self, skill_name: str) -> Optional[AgentSkill]:
        """
        Get skill by name.

        Args:
            skill_name: Name of the skill

        Returns:
            AgentSkill object or None if not found
        """
        return self.skills_cache.get(skill_name)

    def _create_default_agents(self):
        """Create default agents for the system."""
        default_agents = [
            OllamaAgentConfig(
                agent_id="rag_research_agent",
                name="RAG Research Agent",
                description="Specialized in document analysis and research using local RAG",
                model="qwen2.5:3b",
                capabilities=["vector_search", "document_analysis", "llm_inference"],
                skills=[],
                temperature=0.7,
                max_tokens=2048
            ),
            OllamaAgentConfig(
                agent_id="code_review_agent",
                name="Code Review Agent",
                description="Security and performance code analysis using local LLMs",
                model="qwen2.5:3b",
                capabilities=["code_analysis", "security_review", "static_analysis"],
                skills=[],
                temperature=0.5,
                max_tokens=2048
            ),
            OllamaAgentConfig(
                agent_id="vector_data_analyst",
                name="Vector Data Analyst",
                description="Mojo SIMD-optimized vector analysis and data clustering",
                model="qwen2.5:3b",
                capabilities=["vector_analysis", "data_clustering", "similarity_search"],
                skills=[],
                temperature=0.3,
                max_tokens=2048
            )
        ]

        for config in default_agents:
            # Only create if doesn't already exist
            if config.agent_id not in self.active_agents:
                self.active_agents[config.agent_id] = config
                logger.info(f"  ✅ Created default agent: {config.name} ({config.agent_id})")

        # Save default agents to file
        if len(self.active_agents) > 0:
            self._save_agents()

    def _load_agents_from_file(self):
        """Load agents from persistent JSON file."""
        if not self.agents_config_file.exists():
            logger.info("No agents config file found, will create on first save")
            return

        try:
            with open(self.agents_config_file, 'r') as f:
                agents_data = json.load(f)

            for agent_id, agent_dict in agents_data.items():
                # Reconstruct OllamaAgentConfig from dict
                config = OllamaAgentConfig(
                    agent_id=agent_dict['agent_id'],
                    name=agent_dict['name'],
                    description=agent_dict['description'],
                    model=agent_dict.get('model', 'qwen2.5:3b'),
                    capabilities=agent_dict.get('capabilities', []),
                    skills=agent_dict.get('skills', []),
                    temperature=agent_dict.get('temperature', 0.7),
                    max_tokens=agent_dict.get('max_tokens', 2048),
                    status=agent_dict.get('status', 'active')
                )

                # Rebuild system prompt
                config.system_prompt = self._build_system_prompt(config)

                self.active_agents[agent_id] = config

            logger.info(f"✅ Loaded {len(self.active_agents)} agents from {self.agents_config_file}")

        except Exception as e:
            logger.error(f"Failed to load agents from file: {e}")
            logger.info("Will use default agents instead")

    def _save_agents(self):
        """Save agents to persistent JSON file."""
        try:
            # Convert agents to serializable dict
            agents_data = {}
            for agent_id, config in self.active_agents.items():
                agents_data[agent_id] = {
                    'agent_id': config.agent_id,
                    'name': config.name,
                    'description': config.description,
                    'model': config.model,
                    'capabilities': config.capabilities or [],
                    'skills': config.skills or [],
                    'temperature': config.temperature,
                    'max_tokens': config.max_tokens,
                    'status': config.status
                }

            # Write to file
            with open(self.agents_config_file, 'w') as f:
                json.dump(agents_data, f, indent=2)

            logger.info(f"✅ Saved {len(self.active_agents)} agents to {self.agents_config_file}")

        except Exception as e:
            logger.error(f"Failed to save agents to file: {e}")

    def check_ollama_available(self) -> bool:
        """
        Check if Ollama server is available.

        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama not available: {e}")
            return False

    def list_ollama_models(self) -> List[str]:
        """
        List available Ollama models.

        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def create_agent(self, config: OllamaAgentConfig) -> Dict[str, Any]:
        """
        Create and start a new agent with Ollama.

        Args:
            config: Agent configuration

        Returns:
            Agent status dictionary
        """
        # Check if Ollama is available
        if not self.check_ollama_available():
            raise RuntimeError("Ollama server is not available. Please start Ollama first.")

        # Validate skills
        if config.skills:
            for skill_name in config.skills:
                if skill_name not in self.skills_cache:
                    raise ValueError(f"Skill '{skill_name}' not found. Available: {list(self.skills_cache.keys())}")

        # Build system prompt with skills
        system_prompt = self._build_system_prompt(config)
        config.system_prompt = system_prompt

        # Register agent
        self.active_agents[config.agent_id] = config

        # Save to persistent storage
        self._save_agents()

        logger.info(f"✅ Created agent: {config.name} ({config.agent_id})")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Skills: {config.skills or []}")

        return {
            'agent_id': config.agent_id,
            'name': config.name,
            'description': config.description,
            'model': config.model,
            'skills': config.skills or [],
            'status': config.status,
            'capabilities': config.capabilities or [],
            'created_at': time.time()
        }

    def update_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing agent's configuration.

        Args:
            agent_id: ID of the agent to update
            agent_data: Updated agent data (name, description, model, skills, capabilities, temperature, max_tokens)

        Returns:
            Updated agent info dictionary or None if not found
        """
        if agent_id not in self.active_agents:
            return None

        config = self.active_agents[agent_id]

        # Update fields if provided
        if 'name' in agent_data:
            config.name = agent_data['name']
        if 'description' in agent_data:
            config.description = agent_data['description']
        if 'model' in agent_data:
            config.model = agent_data['model']
        if 'capabilities' in agent_data:
            config.capabilities = agent_data['capabilities']
        if 'temperature' in agent_data:
            config.temperature = agent_data['temperature']
        if 'max_tokens' in agent_data:
            config.max_tokens = agent_data['max_tokens']
        if 'skills' in agent_data:
            # Validate skills exist
            for skill_name in agent_data['skills']:
                if skill_name not in self.skills_cache:
                    raise ValueError(f"Skill '{skill_name}' not found. Available: {list(self.skills_cache.keys())}")
            config.skills = agent_data['skills']

        # Rebuild system prompt with new configuration
        config.system_prompt = self._build_system_prompt(config)

        # Save to persistent storage
        self._save_agents()

        logger.info(f"✅ Updated agent: {config.name} ({agent_id})")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Skills: {config.skills or []}")

        return {
            'agent_id': agent_id,
            'name': config.name,
            'description': config.description,
            'model': config.model,
            'skills': config.skills or [],
            'status': config.status,
            'capabilities': config.capabilities or []
        }

    def update_agent_status(self, agent_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """
        Update an agent's active/inactive status.

        Args:
            agent_id: ID of the agent to update
            new_status: New status - "active" or "inactive"

        Returns:
            Updated agent info dictionary or None if not found
        """
        if agent_id not in self.active_agents:
            return None

        if new_status not in ['active', 'inactive']:
            raise ValueError(f"Invalid status: {new_status}. Must be 'active' or 'inactive'")

        config = self.active_agents[agent_id]
        config.status = new_status

        # Save to persistent storage
        self._save_agents()

        logger.info(f"✅ Updated agent status: {config.name} ({agent_id}) -> {new_status}")

        return {
            'agent_id': agent_id,
            'name': config.name,
            'description': config.description,
            'model': config.model,
            'skills': config.skills or [],
            'status': config.status,
            'capabilities': config.capabilities or [],
            'temperature': config.temperature,
            'max_tokens': config.max_tokens
        }

    def _init_tool_registry(self):
        """Initialize the registry of callable tools for agents."""
        self.tools = {}

        if WEB_TOOLS_AVAILABLE:
            self.tools['web_search'] = {
                'function': web_search,
                'description': 'Search the web using DuckDuckGo. Returns list of search results. FOR COMPREHENSIVE RESEARCH: Use max_results=50 and make MULTIPLE searches with different queries.',
                'parameters': {
                    'query': 'Search query string',
                    'max_results': 'Maximum number of results (default: 50, use 50+ for comprehensive searches)',
                    'site': 'Optional site filter (e.g., ".edu" for academic sites)'
                }
            }

            self.tools['web_fetch'] = {
                'function': web_fetch,
                'description': 'Fetch and parse content from a URL. Returns extracted text.',
                'parameters': {
                    'url': 'URL to fetch',
                    'extract_text': 'Whether to extract clean text (default: true)',
                    'max_length': 'Maximum text length (default: 10000)'
                }
            }

            self.tools['search_faculty_hires'] = {
                'function': search_faculty_hires,
                'description': 'Search for recent faculty hires in academic departments. Returns hire records.',
                'parameters': {
                    'department': 'Academic department name (e.g., "political science")',
                    'university': 'Optional university name',
                    'max_results': 'Maximum results (default: 5)'
                }
            }

            self.tools['extract_faculty_profile'] = {
                'function': extract_faculty_profile,
                'description': 'Extract detailed profile from a faculty member\'s webpage. Returns name, position, PhD info, dissertation title/link, research interests.',
                'parameters': {
                    'url': 'URL of the faculty profile page (must be complete URL starting with http/https)'
                }
            }

            logger.info(f"✅ Loaded {len(self.tools)} web tools for agents")
        else:
            logger.warning("Web tools not available - agents cannot perform web searches")

        if SHREDDING_TOOLS_AVAILABLE:
            self.tools['shred_rfp'] = {
                'function': shred_rfp,
                'description': 'Analyze government RFP documents to extract structured requirements. Returns opportunity ID, requirement counts, and compliance matrix path.',
                'parameters': {
                    'file_path': 'Path to RFP PDF or text file (e.g., "data/JADC2/FA8612-21-S-C001.txt")',
                    'rfp_number': 'RFP/solicitation number (e.g., "FA8612-21-S-C001")',
                    'opportunity_name': 'Name of the opportunity (e.g., "JADC2 Cloud Services")',
                    'due_date': 'Proposal due date in YYYY-MM-DD format (e.g., "2025-02-15")',
                    'agency': 'Issuing agency (optional, e.g., "Air Force")',
                    'naics_code': 'NAICS code (optional, e.g., "541512")',
                    'set_aside': 'Set-aside type (optional, e.g., "Small Business")',
                    'create_tasks': 'Whether to create tasks for each requirement (default: true)',
                    'auto_assign': 'Whether to auto-assign tasks to agents (default: false)'
                }
            }

            self.tools['get_opportunity_status'] = {
                'function': get_opportunity_status,
                'description': 'Get status and statistics for a previously shredded RFP opportunity. Returns requirement counts, compliance progress, and task status.',
                'parameters': {
                    'opportunity_id': 'UUID of the opportunity (returned from shred_rfp)'
                }
            }

            self.tools['shred_directory'] = {
                'function': shred_directory,
                'description': 'Process ALL RFP documents in a directory. Use this when asked to process multiple files or "documents" (plural). Automatically extracts RFP numbers from filenames and generates compliance matrices for each file.',
                'parameters': {
                    'directory_path': 'Path to directory containing RFP files (e.g., "data/JADC2")',
                    'default_due_date': 'Default due date for all RFPs in YYYY-MM-DD format (default: "2025-12-31")',
                    'agency': 'Issuing agency (optional, e.g., "Air Force")',
                    'create_tasks': 'Whether to create tasks for each requirement (default: true)'
                }
            }

            logger.info(f"✅ Loaded {len([k for k in self.tools.keys() if k.startswith('shred') or k.startswith('get_opportunity')])} shredding tools for agents")
        else:
            logger.warning("Shredding tools not available - agents cannot shred RFPs")

    def _get_tool_documentation(self, agent_config: 'OllamaAgentConfig' = None) -> str:
        """
        Generate tool documentation for agent system prompts.

        Args:
            agent_config: Agent configuration to filter tools by skills (optional)

        Returns:
            Tool documentation string
        """
        if not self.tools:
            return ""

        # Map skills to their tools
        skill_tool_mapping = {
            'shredding': ['shred_rfp', 'shred_directory', 'get_opportunity_status'],
            'career-researcher': ['web_search', 'web_fetch', 'search_faculty_hires', 'extract_faculty_profile'],
            'career-monster': ['web_search', 'web_fetch', 'search_faculty_hires', 'extract_faculty_profile']
        }

        # Determine which tools this agent can use
        if agent_config and agent_config.skills:
            allowed_tools = set()
            for skill in agent_config.skills:
                if skill in skill_tool_mapping:
                    allowed_tools.update(skill_tool_mapping[skill])

            # Filter tools
            agent_tools = {k: v for k, v in self.tools.items() if k in allowed_tools}
        else:
            # No filtering - show all tools (backward compatibility)
            agent_tools = self.tools

        if not agent_tools:
            return ""

        doc = "\n\n## Available Tools\n\n"
        doc += "You can use the following tools to gather information:\n\n"

        for tool_name, tool_info in agent_tools.items():
            doc += f"### {tool_name}\n"
            doc += f"{tool_info['description']}\n\n"
            doc += "**Parameters:**\n"
            for param, desc in tool_info['parameters'].items():
                doc += f"- `{param}`: {desc}\n"
            doc += "\n**Usage:**\n"
            doc += f"```\n[TOOL_CALL:{tool_name}]\n"
            doc += json.dumps({"param1": "value1", "param2": "value2"}, indent=2)
            doc += "\n[/TOOL_CALL]\n```\n\n"

        doc += "**CRITICAL FORMATTING:** Every tool call MUST have BOTH opening and closing tags:\n"
        doc += "✅ CORRECT: [TOOL_CALL:web_search]{\"query\":\"test\"}[/TOOL_CALL]\n"
        doc += "❌ WRONG: [TOOL_CALL:web_search]{\"query\":\"test\"} (missing closing tag - won't execute!)\n\n"
        doc += "**CRITICAL:** Your FIRST response MUST include a tool call. Do NOT respond with explanations of what you would need - USE THE TOOLS IMMEDIATELY. You have the tools - USE THEM.\n\n"

        return doc

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from agent response.

        Args:
            response: Agent's response text

        Returns:
            List of tool call dictionaries with tool_name and parameters
        """
        tool_calls = []

        # Pattern: [TOOL_CALL:tool_name]...json...[/TOOL_CALL]
        pattern = r'\[TOOL_CALL:(\w+)\](.*?)\[/TOOL_CALL\]'
        matches = re.finditer(pattern, response, re.DOTALL)

        for match in matches:
            tool_name = match.group(1)
            json_str = match.group(2).strip()

            try:
                parameters = json.loads(json_str)
                tool_calls.append({
                    'tool_name': tool_name,
                    'parameters': parameters
                })
                logger.info(f"Parsed tool call: {tool_name} with params: {list(parameters.keys())}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool call JSON for {tool_name}: {e}")

        # Fallback: Check for incomplete tool calls (missing closing tag)
        if not tool_calls and '[TOOL_CALL:' in response:
            logger.warning("⚠️  Found incomplete tool call (missing [/TOOL_CALL] closing tag)")
            # Try to extract incomplete tool calls
            incomplete_pattern = r'\[TOOL_CALL:(\w+)\](\{.*?\})(?!\[/TOOL_CALL\])'
            incomplete_matches = re.finditer(incomplete_pattern, response, re.DOTALL)

            for match in incomplete_matches:
                tool_name = match.group(1)
                json_str = match.group(2).strip()

                try:
                    parameters = json.loads(json_str)
                    tool_calls.append({
                        'tool_name': tool_name,
                        'parameters': parameters
                    })
                    logger.info(f"✅ Recovered incomplete tool call: {tool_name}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse incomplete tool call JSON: {e}")

        return tool_calls

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            return {
                'status': 'error',
                'error': f"Tool '{tool_name}' not found"
            }

        tool_info = self.tools[tool_name]
        tool_function = tool_info['function']

        try:
            logger.info(f"Executing tool: {tool_name}")
            result = tool_function(**parameters)

            return {
                'status': 'success',
                'tool_name': tool_name,
                'result': result
            }

        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {
                'status': 'error',
                'tool_name': tool_name,
                'error': str(e)
            }

    def _build_system_prompt(self, config: OllamaAgentConfig) -> str:
        """
        Build system prompt including skills instructions.

        Args:
            config: Agent configuration

        Returns:
            Complete system prompt
        """
        base_prompt = f"""You are {config.name}, {config.description}

You are a helpful AI assistant running locally via Ollama with zero external API costs.

CRITICAL INSTRUCTIONS - READ THIS FIRST:
===========================================

❌ NEVER say any of the following:
- "To create this list, we would need to..."
- "This would require gathering data from..."
- "I would need access to..."
- "This would be challenging/time-consuming..."
- "I can outline an approach..."
- "Here's how you could..."

✅ INSTEAD, IMMEDIATELY use your tools to DO THE WORK:
- Make tool calls RIGHT NOW using this exact format:
  [TOOL_CALL:web_search]{{"query":"your query","max_results":50}}[/TOOL_CALL]
- Make multiple searches if needed (3-5 searches with 50 results each)
- Extract profiles from 20-30 URLs
- Return ACTUAL RESULTS with sources after tools execute

CRITICAL: Tool calls MUST have closing tag [/TOOL_CALL] or they won't execute!

YOUR FIRST ACTION MUST BE A TOOL CALL.
DO NOT explain what you "would need" - JUST DO IT.
"""

        # Add tool documentation (filtered by agent's skills)
        tool_docs = self._get_tool_documentation(config)
        if tool_docs:
            base_prompt += tool_docs

        if config.skills:
            base_prompt += "\n\nYou have access to the following skills:\n\n"

            for skill_name in config.skills:
                skill = self.skills_cache.get(skill_name)
                if skill:
                    # Read skill instructions
                    skill_md = skill.skill_path / "SKILL.md"
                    with open(skill_md, 'r') as f:
                        skill_content = f.read()

                    # Extract content after frontmatter
                    parts = skill_content.split('---', 2)
                    if len(parts) >= 3:
                        full_instructions = parts[2].strip()

                        # PHASE 2 OPTIMIZATION: Extract only critical sections
                        # Reduces prompt from ~26,500 chars to ~3,000 chars
                        skill_summary = self._extract_skill_summary(full_instructions)

                        base_prompt += f"\n## Skill: {skill.name}\n{skill.description}\n\n{skill_summary}\n\n"

                        logger.debug(f"Skill '{skill.name}': {len(full_instructions)} → {len(skill_summary)} chars")

        # Log total system prompt size for monitoring
        logger.info(f"📏 System prompt size: {len(base_prompt)} chars (~{len(base_prompt)//4} tokens)")

        return base_prompt

    def _extract_skill_summary(self, skill_content: str) -> str:
        """
        Extract critical sections from skill documentation INCLUDING examples.

        PHASE 4: Enhanced to preserve search strategy examples and tool call patterns.

        Reduces prompt size by extracting only:
        - What NOT to Do section
        - Required Workflow section (with examples!)
        - Mandatory Process section
        - Critical Instructions
        - Search Strategy examples

        Args:
            skill_content: Full SKILL.md content

        Returns:
            Condensed summary with critical examples preserved
        """
        lines = skill_content.split('\n')
        summary_lines = []
        include = False
        current_section = None
        section_line_count = 0
        in_code_block = False
        max_lines_per_section = 50  # PHASE 4: Increased from 25 to 50 for examples

        # Critical section headers to include
        critical_sections = [
            '## What NOT to Do',
            '## Required Workflow',
            '## Mandatory Process',
            '## MANDATORY PROCESS',
            '## Required Output Format',
            '## CRITICAL INSTRUCTIONS',
            '## Query Diversity Requirements',  # PHASE 4: New section
        ]

        for line in lines:
            # Track code blocks - never truncate inside them
            if line.strip().startswith('```') or '[TOOL_CALL:' in line:
                in_code_block = not in_code_block

            # Check if this is a critical section header
            is_critical_header = any(line.startswith(section) for section in critical_sections)

            if is_critical_header:
                include = True
                current_section = line
                section_line_count = 0
                summary_lines.append('\n' + line)
            elif line.startswith('##') and include and not in_code_block:
                # Hit a new section, stop including previous (unless in code block)
                include = False
                current_section = None
            elif include:
                # PHASE 4: Always include if in code block (preserve examples)
                if in_code_block or section_line_count < max_lines_per_section:
                    summary_lines.append(line)
                    section_line_count += 1
                elif section_line_count == max_lines_per_section and not in_code_block:
                    summary_lines.append('... [additional content truncated]')
                    section_line_count += 1

        # If we got very little, include the overview section too
        if len(summary_lines) < 10:
            for line in lines[:30]:  # First 30 lines usually have overview
                if line.startswith('#') and 'Overview' in line:
                    include = True
                elif line.startswith('##') and include:
                    break
                elif include:
                    summary_lines.insert(0, line)

        result = '\n'.join(summary_lines[:150])  # PHASE 4: Increased from 100 to 150 lines
        logger.debug(f"Skill summary: {len(skill_content)} chars → {len(result)} chars ({len(result)/len(skill_content)*100:.1f}%)")
        return result

    def invoke_agent(self, agent_id: str, user_message: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke an agent to process a user message with tool calling support.

        Args:
            agent_id: ID of the agent to invoke
            user_message: User's message/query
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Agent response dictionary
        """
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent '{agent_id}' not found")

        config = self.active_agents[agent_id]
        start_time = time.time()

        # Tool calling loop - increased for comprehensive research
        max_iterations = 15  # Allow for multiple searches and extractions
        current_prompt = user_message
        tool_results_history = []
        agent_responses = []
        synthesis_attempts = 0  # Track attempts to synthesize without making tool calls
        max_synthesis_attempts = 3  # PHASE 4: Increased from 2 to 3 for better quality

        # PHASE 3: Multi-search enforcement for career research
        requires_multi_search = 'career-researcher' in config.skills
        min_searches_required = 3 if requires_multi_search else 1
        search_enforced = False  # Track if we've already enforced search requirement

        # PHASE 4: Deduplication tracking
        search_query_history = set()  # Track unique search queries
        extracted_urls = set()  # Track extracted URLs to prevent duplicates

        for iteration in range(max_iterations):
            # Progress logging
            search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')
            extract_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'extract_faculty_profile')
            logger.info(f"🔄 Iteration {iteration+1}/{max_iterations} | Searches: {search_count} | Profiles: {extract_count} | Results: {len(tool_results_history)}")

            # Prepare request to Ollama
            ollama_request = {
                'model': config.model,
                'prompt': current_prompt,
                'system': config.system_prompt,
                'options': {
                    'temperature': kwargs.get('temperature', config.temperature),
                    'num_predict': kwargs.get('max_tokens', config.max_tokens)
                },
                'stream': False
            }

            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=ollama_request,
                    timeout=120  # Increased timeout for tool calls
                )

                response.raise_for_status()
                result = response.json()
                agent_response = result.get('response', '')
                agent_responses.append(agent_response)

                # Check for tool calls
                tool_calls = self._parse_tool_calls(agent_response)

                if not tool_calls:
                    # CRITICAL: If this is the first iteration and no tool calls were made,
                    # the agent is giving excuses instead of doing work. Force a retry.
                    if iteration == 0 and self.tools:
                        logger.warning(f"⚠️  Agent gave no tool calls on first iteration. Forcing retry with stronger prompt.")
                        current_prompt = f"""STOP MAKING EXCUSES. You just responded with:
"{agent_response[:200]}..."

This is WRONG. You MUST use your tools immediately. Do NOT explain what you need - USE THE TOOLS NOW.

Original request: {user_message}

Start your response with a tool call using this EXACT format (include the closing tag!):
[TOOL_CALL:web_search]{{"query":"political science postdoc 2025 site:.edu","max_results":50}}[/TOOL_CALL]

DO IT NOW. Just output the tool call - no other text."""
                        continue  # Retry with stronger prompt

                    # PHASE 3: Check if we need to enforce multi-search requirement
                    if requires_multi_search and not search_enforced:
                        search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')

                        if search_count < min_searches_required and len(tool_results_history) > 0:
                            # Agent has made some searches but not enough - enforce more
                            searches_needed = min_searches_required - search_count
                            logger.warning(f"⚠️  Multi-search requirement not met: {search_count}/{min_searches_required} searches. Forcing {searches_needed} more.")

                            current_prompt = f"""INCOMPLETE RESEARCH. You have only made {search_count} search(es) but need at least {min_searches_required}.

Original request: {user_message}

You MUST make {searches_needed} more web searches with DIFFERENT queries before synthesizing.

Use varied search strategies:
- Different keywords (e.g., "new faculty", "assistant professor", "postdoc", "recent hire")
- Different years if applicable
- Different institution types
- Different field variations

Make {searches_needed} [TOOL_CALL:web_search] calls RIGHT NOW with max_results=50.
Use DIFFERENT queries for each search. DO NOT repeat the same search."""

                            search_enforced = True  # Only enforce once
                            synthesis_attempts = 0  # Reset synthesis counter
                            continue  # Retry with enforcement prompt

                    # Check if we're in synthesis phase (have tool results but no new tool calls)
                    if len(tool_results_history) > 0:
                        synthesis_attempts += 1
                        logger.info(f"📝 Synthesis attempt {synthesis_attempts}/{max_synthesis_attempts} | Searches: {sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')}/{min_searches_required}")

                        if synthesis_attempts >= max_synthesis_attempts:
                            # PHASE 4: Validate diversity before forcing completion
                            unique_queries = len(search_query_history)
                            final_search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')

                            # If multi-search required, ensure we have enough UNIQUE queries
                            if requires_multi_search and unique_queries < min_searches_required:
                                logger.warning(f"⚠️  Insufficient unique queries: {unique_queries}/{min_searches_required}. Forcing more searches.")

                                current_prompt = f"""INSUFFICIENT SEARCH DIVERSITY

You have only made {unique_queries} UNIQUE search(es) but need {min_searches_required}.

Your searches so far:
{chr(10).join(f'   {i+1}. "{q}"' for i, q in enumerate(sorted(search_query_history)))}

Original request: {user_message}

Make {min_searches_required - unique_queries} MORE searches with completely DIFFERENT queries.
Use the diversity guidelines: different roles, institutions, time periods, keywords.
Each search should return NEW results, not duplicates."""

                                synthesis_attempts = 0  # Reset to allow more attempts
                                continue  # Force another iteration

                            # OK to force completion - we have diverse data
                            logger.info(f"✅ Forcing completion after {synthesis_attempts} synthesis attempts | Unique queries: {unique_queries} | Tool calls: {len(tool_results_history)}")
                            elapsed_time = time.time() - start_time

                            return {
                                'status': 'success',
                                'agent_id': agent_id,
                                'response': agent_response,
                                'model': config.model,
                                'elapsed_time_ms': int(elapsed_time * 1000),
                                'cost': 0.00,
                                'tool_calls_made': len(tool_results_history),
                                'searches_made': final_search_count,
                                'searches_required': min_searches_required if requires_multi_search else None,
                                'unique_queries': unique_queries,
                                'unique_urls': len(extracted_urls),
                                'iterations': iteration + 1,
                                'total_duration': result.get('total_duration', 0),
                                'eval_count': result.get('eval_count', 0),
                                'forced_completion': True
                            }

                    # No more tool calls - this is the final response
                    final_search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')
                    elapsed_time = time.time() - start_time

                    # PHASE 4: Comprehensive completion logging
                    logger.info(f"""
📊 Agent Research Complete:
   Iterations: {iteration + 1}/{max_iterations}
   Unique Searches: {len(search_query_history)}
   Unique URLs Extracted: {len(extracted_urls)}
   Total Tool Calls: {len(tool_results_history)}
   Elapsed Time: {elapsed_time:.1f}s

   Search Queries Used:
{chr(10).join(f'      {i+1}. "{q}"' for i, q in enumerate(sorted(search_query_history)))}
""")

                    return {
                        'status': 'success',
                        'agent_id': agent_id,
                        'response': agent_response,
                        'model': config.model,
                        'elapsed_time_ms': int(elapsed_time * 1000),
                        'cost': 0.00,  # Zero cost - local Ollama
                        'tool_calls_made': len(tool_results_history),
                        'searches_made': final_search_count,
                        'searches_required': min_searches_required if requires_multi_search else None,
                        'unique_queries': len(search_query_history),
                        'unique_urls': len(extracted_urls),
                        'iterations': iteration + 1,
                        'total_duration': result.get('total_duration', 0),
                        'eval_count': result.get('eval_count', 0)
                    }
                else:
                    # Tool calls made - reset synthesis counter
                    synthesis_attempts = 0

                # Execute tool calls with deduplication
                tool_results = []
                duplicate_query_detected = False

                for tool_call in tool_calls:
                    tool_name = tool_call['tool_name']
                    parameters = tool_call['parameters']

                    # PHASE 4: Check for duplicate search queries
                    if tool_name == 'web_search':
                        query = parameters.get('query', '').lower().strip()

                        if query in search_query_history:
                            logger.warning(f"⚠️  Duplicate search query detected: '{query}'")
                            duplicate_query_detected = True

                            # Add error result instead of executing
                            tool_results.append({
                                'status': 'skipped',
                                'tool_name': tool_name,
                                'result': {'error': f'Duplicate query: {query}', 'items': []}
                            })
                            continue

                        # Record unique query
                        search_query_history.add(query)
                        logger.info(f"🔍 New unique search: '{query}' (Total unique: {len(search_query_history)})")

                    # PHASE 4: Check for duplicate URL extractions
                    elif tool_name == 'extract_faculty_profile':
                        url = parameters.get('url', '')

                        if url in extracted_urls:
                            logger.info(f"⏭️  Skipping duplicate URL: {url}")

                            # Add skipped result
                            tool_results.append({
                                'status': 'skipped',
                                'tool_name': tool_name,
                                'result': {'message': 'Already extracted this URL', 'name': None}
                            })
                            continue

                        # Record unique URL
                        extracted_urls.add(url)

                    # Execute the tool
                    result = self._execute_tool(tool_name, parameters)
                    tool_results.append(result)
                    tool_results_history.append(result)

                # PHASE 4: Diversity enforcement - if duplicate detected, force retry with guidance
                if duplicate_query_detected:
                    logger.warning(f"🔄 Forcing diversity retry due to duplicate query")

                    current_prompt = f"""❌ DUPLICATE SEARCH DETECTED

You just tried to search with a query you already used before.

Already searched queries:
{chr(10).join(f'   - "{q}"' for q in sorted(search_query_history))}

Original user request: {user_message}

Generate a NEW, DIFFERENT search query using:
- Different role keywords (try: 'postdoc', 'lecturer', 'visiting professor', 'research fellow')
- Different action verbs (try: 'appointed', 'hired', 'joining', 'welcomes', 'announces')
- Different institution tiers (try: 'liberal arts college', 'R2 university', 'public university')
- Different geographic focus (try: 'midwest', 'west coast', 'ivy league', 'UC system')
- Different time periods (try: 'fall 2024', 'spring 2025', 'academic year 2024-2025')

Make a NEW [TOOL_CALL:web_search] with max_results=50 using a completely different query. DO NOT repeat any query above."""

                    continue  # Skip to next iteration with diversity prompt

                # PHASE 3: Check if multi-search requirement is now met
                if requires_multi_search and not search_enforced:
                    current_search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')
                    if current_search_count >= min_searches_required:
                        logger.info(f"✅ Multi-search requirement met: {current_search_count}/{min_searches_required} searches completed")

                # Build prompt for next iteration with tool results
                results_text = "\n\n[TOOL_RESULTS]\n"
                for i, tr in enumerate(tool_results, 1):
                    results_text += f"\nResult {i} ({tr.get('tool_name', 'unknown')}):\n"
                    if tr['status'] == 'success':
                        # Format result nicely
                        result_data = tr['result']
                        if isinstance(result_data, list):
                            results_text += f"Found {len(result_data)} items:\n"
                            results_text += json.dumps(result_data[:10], indent=2)  # Limit to first 10
                            if len(result_data) > 10:
                                results_text += f"\n... and {len(result_data) - 10} more"
                        else:
                            results_text += json.dumps(result_data, indent=2)
                    else:
                        results_text += f"Error: {tr.get('error', 'Unknown error')}\n"

                results_text += "\n[/TOOL_RESULTS]\n\n"

                # CRITICAL: Preserve context - include original user request
                current_prompt = f"""ORIGINAL USER REQUEST: {user_message}

{results_text}

Now provide your final, formatted response answering the user's request above.

IMPORTANT:
- List each hire with: Name, Position, Institution, PhD info, Source URL
- DO NOT make more tool calls unless you need additional data
- If you have sufficient results, synthesize them now
- Use clear formatting"""

            except requests.exceptions.RequestException as e:
                logger.error(f"Ollama request failed: {e}")
                return {
                    'status': 'error',
                    'agent_id': agent_id,
                    'error': str(e),
                    'cost': 0.00
                }

        # Max iterations reached
        final_search_count = sum(1 for tr in tool_results_history if tr.get('tool_name') == 'web_search')
        elapsed_time = time.time() - start_time

        # PHASE 4: Log max iterations with full stats
        logger.warning(f"""
⚠️  Max Iterations Reached:
   Iterations: {max_iterations}/{max_iterations}
   Unique Searches: {len(search_query_history)}
   Unique URLs: {len(extracted_urls)}
   Tool Calls: {len(tool_results_history)}

   Queries Used:
{chr(10).join(f'      - "{q}"' for q in sorted(search_query_history))}
""")

        return {
            'status': 'success',
            'agent_id': agent_id,
            'response': agent_responses[-1] if agent_responses else "Max iterations reached",
            'model': config.model,
            'elapsed_time_ms': int(elapsed_time * 1000),
            'cost': 0.00,
            'tool_calls_made': len(tool_results_history),
            'searches_made': final_search_count,
            'searches_required': min_searches_required if requires_multi_search else None,
            'unique_queries': len(search_query_history),
            'unique_urls': len(extracted_urls),
            'iterations': max_iterations,
            'warning': 'Max iterations reached'
        }

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: ID of the agent to delete

        Returns:
            True if deleted, False if not found
        """
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]

            # Save to persistent storage
            self._save_agents()

            logger.info(f"✅ Deleted agent: {agent_id}")
            return True
        return False

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all agents (both active and inactive).

        Returns:
            List of agent info dictionaries
        """
        return [
            {
                'agent_id': agent_id,
                'name': config.name,
                'description': config.description,
                'model': config.model,
                'skills': config.skills or [],
                'status': config.status,
                'capabilities': config.capabilities or []
            }
            for agent_id, config in self.active_agents.items()
        ]

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent info dictionary or None if not found
        """
        if agent_id not in self.active_agents:
            return None

        config = self.active_agents[agent_id]
        return {
            'agent_id': agent_id,
            'name': config.name,
            'description': config.description,
            'model': config.model,
            'skills': config.skills or [],
            'capabilities': config.capabilities or [],
            'system_prompt': config.system_prompt,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'status': config.status
        }


# Singleton instance
_runtime_instance: Optional[OllamaAgentRuntime] = None


def get_runtime() -> OllamaAgentRuntime:
    """
    Get the singleton Ollama agent runtime instance.

    Returns:
        OllamaAgentRuntime instance
    """
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = OllamaAgentRuntime()
    return _runtime_instance


# For testing
if __name__ == "__main__":
    runtime = get_runtime()

    print("\n=== Available Skills ===")
    for skill in runtime.list_skills():
        print(f"  - {skill['name']}: {skill['description']}")

    print("\n=== Ollama Status ===")
    if runtime.check_ollama_available():
        print("  ✅ Ollama is available")
        models = runtime.list_ollama_models()
        print(f"  Available models: {models}")
    else:
        print("  ❌ Ollama is not available")

    print("\n=== Creating Test Agent ===")
    config = OllamaAgentConfig(
        agent_id="test_agent_001",
        name="Test Agent",
        description="A test agent with PDF skill from Anthropic plugin",
        model="qwen2.5:3b",
        capabilities=["pdf_processing", "data_analysis"],
        skills=["pdf"]
    )

    try:
        agent = runtime.create_agent(config)
        print(f"  ✅ Created: {agent['name']}")

        # Test invocation
        print("\n=== Testing Agent Invocation ===")
        response = runtime.invoke_agent(
            "test_agent_001",
            "How do I extract text from a PDF file?"
        )

        if response['status'] == 'success':
            print(f"  ✅ Response (took {response['elapsed_time_ms']}ms):")
            print(f"  {response['response'][:200]}...")
        else:
            print(f"  ❌ Error: {response.get('error')}")

    except Exception as e:
        print(f"  ❌ Error: {e}")
