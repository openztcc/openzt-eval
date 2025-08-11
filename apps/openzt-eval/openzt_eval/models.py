"""Model loading and management."""

from enum import Enum
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
import logging
import os

try:
    from lmstudio import Client as LMStudioClient
except ImportError:
    LMStudioClient = None

try:
    from braintrust import wrap_openai
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    wrap_openai = None
    OpenAI = None
    AsyncOpenAI = None

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of models supported."""
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a model."""
    name: str
    type: ModelType
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class BaseModel:
    """Base class for model implementations."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the model."""
        raise NotImplementedError


class LocalModel(BaseModel):
    """Local model using LMStudio."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if LMStudioClient is None:
            raise ImportError("lmstudio package is required for local models. Install with: pip install lmstudio")
        
        # Initialize LMStudio client
        endpoint = config.endpoint or "http://localhost:1234"
        self.client = LMStudioClient(base_url=endpoint)
        self.model_id = config.model_id or config.name
        
        logger.info(f"Initialized local model {self.model_id} at {endpoint}")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using LMStudio."""
        try:
            # Merge default parameters with kwargs
            params = {**self.config.parameters, **kwargs}
            
            # Use LMStudio client to generate
            response = self.client.completions.create(
                model=self.model_id,
                prompt=prompt,
                max_tokens=params.get("max_tokens", 1000),
                temperature=params.get("temperature", 0.7),
            )
            
            return response.choices[0].text
        except Exception as e:
            logger.error(f"Error generating from local model {self.model_id}: {e}")
            raise


class RemoteModel(BaseModel):
    """Remote model using OpenAI-compatible API via Braintrust proxy."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        if OpenAI is None or wrap_openai is None:
            raise ImportError("openai and braintrust packages are required for remote models. Install with: pip install openai braintrust")
        
        # Get API key from config or environment
        api_key = config.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("BRAINTRUST_API_KEY")
        
        # Determine base URL based on model type
        if config.endpoint:
            base_url = config.endpoint
        elif config.type == ModelType.OPENAI:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        else:
            # Use Braintrust proxy for other model types
            base_url = os.getenv("BRAINTRUST_API_URL", "https://api.braintrust.dev/v1/proxy")
        
        # Create OpenAI client
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Wrap with Braintrust for logging
        if wrap_openai:
            self.client = wrap_openai(self.client)
        
        # Determine model ID
        if config.model_id:
            self.model_id = config.model_id
        elif config.type == ModelType.OPENAI:
            self.model_id = "gpt-4"
        elif config.type == ModelType.ANTHROPIC:
            self.model_id = "claude-3-opus-20240229"
        elif config.type == ModelType.GEMINI:
            self.model_id = "gemini-pro"
        else:
            self.model_id = config.name
        
        logger.info(f"Initialized remote model {config.name} using {self.model_id} at {base_url}")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI-compatible API."""
        try:
            # Merge default parameters with kwargs
            params = {**self.config.parameters, **kwargs}
            
            # Use chat completions API
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=params.get("max_tokens", 1000),
                temperature=params.get("temperature", 0.7),
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating from remote model {self.config.name}: {e}")
            raise


class ModelLoader:
    """Loads and manages models."""
    
    def __init__(self):
        self.models: Dict[str, BaseModel] = {}
    
    def load_model(self, config: ModelConfig) -> BaseModel:
        """Load a model based on its configuration."""
        if config.name in self.models:
            logger.info(f"Model {config.name} already loaded")
            return self.models[config.name]
        
        # Create appropriate model instance
        if config.type == ModelType.LOCAL:
            model = LocalModel(config)
        else:
            # All remote models use the RemoteModel class with OpenAI-compatible API
            model = RemoteModel(config)
        
        self.models[config.name] = model
        logger.info(f"Loaded model {config.name} (type: {config.type.value})")
        return model
    
    def load_models(self, configs: List[ModelConfig]) -> Dict[str, BaseModel]:
        """Load multiple models."""
        for config in configs:
            self.load_model(config)
        return self.models
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """Get a loaded model by name."""
        return self.models.get(name)
    
    async def generate_all(self, prompt: str, **kwargs) -> Dict[str, str]:
        """Generate responses from all loaded models."""
        results = {}
        for name, model in self.models.items():
            try:
                results[name] = await model.generate(prompt, **kwargs)
            except Exception as e:
                logger.error(f"Error generating from {name}: {e}")
                results[name] = f"ERROR: {str(e)}"
        return results