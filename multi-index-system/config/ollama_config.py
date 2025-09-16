"""
Ollama Configuration and Client

Provides local LLM integration for entity extraction and embedding generation.
Handles graceful fallbacks when Ollama is not available.
"""

import logging
import json
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaConfig:
    """
    Ollama client for local LLM operations.

    Provides entity extraction, embeddings, and chat capabilities
    with graceful fallbacks when Ollama is unavailable.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available = False
        self.available_models = []

        # Check if Ollama is available
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [model['name'] for model in data.get('models', [])]
                self.available = True
                logger.info(f"Ollama available with {len(self.available_models)} models")
                return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")

        self.available = False
        return False

    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available."""
        if not self.available:
            return False

        # Check exact match or partial match for model names
        for available_model in self.available_models:
            if model_name in available_model or available_model.startswith(model_name):
                return True

        return False

    def generate_embedding(self, model: str, text: str) -> Optional[Dict[str, Any]]:
        """Generate embedding for text using Ollama."""
        if not self.available:
            logger.warning("Ollama not available for embedding generation")
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ollama embedding failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Ollama embedding request failed: {e}")
            return None

    def chat_response(self, model: str, messages: List[Dict[str, str]],
                     stream: bool = False) -> Optional[Dict[str, Any]]:
        """Get chat response from Ollama model."""
        if not self.available:
            logger.warning("Ollama not available for chat")
            return None

        try:
            # Convert messages to Ollama format
            if isinstance(messages, list) and len(messages) > 0:
                if isinstance(messages[0], dict) and 'content' in messages[0]:
                    # Extract content from message format
                    prompt = messages[-1]['content']
                else:
                    prompt = str(messages[0])
            else:
                prompt = str(messages)

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json" if "json" in prompt.lower() else None
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()

                # Parse JSON response if requested
                if "json" in prompt.lower() and 'response' in data:
                    try:
                        parsed_response = json.loads(data['response'])
                        return {'content': parsed_response}
                    except json.JSONDecodeError:
                        # Return raw response if JSON parsing fails
                        return {'content': data['response']}

                return {'content': data.get('response', '')}
            else:
                logger.error(f"Ollama chat failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Ollama chat request failed: {e}")
            return None

    def extract_entities_from_text(self, text: str, model: str = "llama3.2:1b") -> List[Dict[str, Any]]:
        """Extract entities from text using Ollama."""
        if not self.available or not self.is_model_available(model):
            logger.warning(f"Ollama or model {model} not available for entity extraction")
            return self._fallback_entity_extraction(text)

        prompt = f"""Extract named entities from the following text. Return a JSON list of entities with their types and relationships.

Text: "{text}"

Return JSON format:
[
  {{"entity": "Entity Name", "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT", "confidence": 0.9}},
  ...
]

Only return the JSON array, no other text."""

        messages = [{"role": "user", "content": prompt}]
        response = self.chat_response(model, messages)

        if response and 'content' in response:
            try:
                if isinstance(response['content'], list):
                    return response['content']
                elif isinstance(response['content'], str):
                    # Try to parse JSON from string response
                    import re
                    json_match = re.search(r'\[.*\]', response['content'], re.DOTALL)
                    if json_match:
                        entities = json.loads(json_match.group())
                        return entities if isinstance(entities, list) else []
            except Exception as e:
                logger.error(f"Failed to parse entity extraction response: {e}")

        return self._fallback_entity_extraction(text)

    def _fallback_entity_extraction(self, text: str) -> List[Dict[str, Any]]:
        """Fallback entity extraction using simple patterns."""
        entities = []

        # Simple pattern-based entity extraction
        words = text.split()

        for i, word in enumerate(words):
            # Detect capitalized words as potential entities
            if word.isalpha() and word[0].isupper() and len(word) > 2:
                # Check if it's likely a person name (followed by surname)
                if i < len(words) - 1 and words[i + 1].isalpha() and words[i + 1][0].isupper():
                    entities.append({
                        "entity": f"{word} {words[i + 1]}",
                        "type": "PERSON",
                        "confidence": 0.6
                    })
                # Check for organization indicators
                elif any(indicator in text.lower() for indicator in ['university', 'company', 'corp', 'inc']):
                    entities.append({
                        "entity": word,
                        "type": "ORGANIZATION",
                        "confidence": 0.5
                    })
                else:
                    entities.append({
                        "entity": word,
                        "type": "CONCEPT",
                        "confidence": 0.4
                    })

        # Remove duplicates and limit results
        seen = set()
        unique_entities = []
        for entity in entities:
            entity_key = entity['entity'].lower()
            if entity_key not in seen and len(entity['entity']) > 2:
                seen.add(entity_key)
                unique_entities.append(entity)

        return unique_entities[:20]  # Limit to 20 entities

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        if not self.available:
            self._check_availability()

        return self.available_models

    def get_status(self) -> Dict[str, Any]:
        """Get Ollama service status."""
        return {
            "available": self.available,
            "base_url": self.base_url,
            "models_count": len(self.available_models),
            "available_models": self.available_models,
            "last_checked": datetime.now().isoformat()
        }