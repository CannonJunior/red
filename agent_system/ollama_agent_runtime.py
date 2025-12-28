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
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests

# Import path utilities
from project_paths import get_project_root, resolve_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
"""

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
                        skill_instructions = parts[2].strip()
                        base_prompt += f"\n## Skill: {skill.name}\n{skill.description}\n\n{skill_instructions}\n\n"

        return base_prompt

    def invoke_agent(self, agent_id: str, user_message: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke an agent to process a user message.

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

        # Prepare request to Ollama
        ollama_request = {
            'model': config.model,
            'prompt': user_message,
            'system': config.system_prompt,
            'options': {
                'temperature': kwargs.get('temperature', config.temperature),
                'num_predict': kwargs.get('max_tokens', config.max_tokens)
            },
            'stream': False
        }

        try:
            start_time = time.time()

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            elapsed_time = time.time() - start_time

            return {
                'status': 'success',
                'agent_id': agent_id,
                'response': result.get('response', ''),
                'model': config.model,
                'elapsed_time_ms': int(elapsed_time * 1000),
                'cost': 0.00,  # Zero cost - local Ollama
                'total_duration': result.get('total_duration', 0),
                'eval_count': result.get('eval_count', 0)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            return {
                'status': 'error',
                'agent_id': agent_id,
                'error': str(e),
                'cost': 0.00
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
