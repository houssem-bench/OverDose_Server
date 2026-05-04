"""
Centralized configuration for OVERDOSE Axe 3.
Uses pydantic-settings for type-safe environment variable loading.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048

    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 8003

    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    LOGS_DIR: str = "logs"

    RL_TOTAL_TIMESTEPS: int = 100000
    RL_LEARNING_RATE: float = 0.0003
    RL_BATCH_SIZE: int = 64
    RL_GAMMA: float = 0.99

    SCRAPE_MAX_PRODUCTS: int = 500
    SCRAPE_MAX_EDC: int = 150
    SCRAPE_DELAY: float = 0.5

    OPEN_BEAUTY_FACTS_URL: str = "https://world.openbeautyfacts.org"
    OPEN_FOOD_FACTS_URL: str = "https://world.openfoodfacts.org"
    PUBCHEM_API_URL: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    EPA_COMPTOX_URL: str = "https://comptox.epa.gov/dashboard"
    GROQ_API_URL: str = "https://api.groq.com/openai/v1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("GROQ_API_KEY")
    @classmethod
    def validate_groq_key(cls, v):
        if not v or v == "gsk_your_key_here":
            import warnings

            warnings.warn(
                "GROQ_API_KEY not set. LLM features will be disabled. "
                "Get a free key at https://console.groq.com"
            )
        return v

    def ensure_dirs(self):
        """Create data/models/logs directories if they don't exist."""
        for d in [self.DATA_DIR, self.MODELS_DIR, self.LOGS_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)

    @property
    def edc_database_path(self) -> Path:
        return Path(self.DATA_DIR) / "edc_database.json"

    @property
    def products_path(self) -> Path:
        return Path(self.DATA_DIR) / "products.json"

    @property
    def alternatives_path(self) -> Path:
        return Path(self.DATA_DIR) / "alternatives.json"

    @property
    def tunisia_products_path(self) -> Path:
        return Path(self.DATA_DIR) / "tunisia_products.json"

    @property
    def model_path(self) -> Path:
        return Path(self.MODELS_DIR) / "dqn_recommender"

    @property
    def training_curve_path(self) -> Path:
        return Path(self.LOGS_DIR) / "training_curve.png"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
