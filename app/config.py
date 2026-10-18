import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    url: str = os.getenv('FALKORDB_URL', 'redis://localhost:6379')
    prefix: str = os.getenv('GRAPH_PREFIX', 'memrelay')
    llm_mode: str = os.getenv('LLM_MODE', 'mock')
    llm_model: str = os.getenv('LLM_MODEL', 'gemini/gemini-2.5-flash')
