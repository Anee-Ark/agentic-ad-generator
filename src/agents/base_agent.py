from abc import ABC, abstractmethod
from typing import Dict, Any, List
import os
import logging

import anthropic
from dotenv import load_dotenv

load_dotenv()


class BaseAgent(ABC):
    """Base class for all agents in the system"""

    def __init__(self, name: str, model: str = "claude-sonnet-4-5-20250929"):
        self.name = name
        self.model = model

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )

        self.client = anthropic.Anthropic(api_key=api_key)

        # Use a per-agent logger name (nice for debugging multi-agent runs)
        self.logger = logging.getLogger(name)
        if not logging.getLogger().handlers:
            logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method - must be implemented by each agent"""
        raise NotImplementedError

    def call_llm(self, prompt: str, system_prompt: str = None, temperature: float = 0.7) -> str:
        """Helper method to call Claude API"""
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise

    def validate_input(self, input_data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate that input contains required fields"""
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
        return True

