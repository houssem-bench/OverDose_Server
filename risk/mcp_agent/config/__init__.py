import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env without printing anything
dotenv_path = None
for root in [Path(__file__).parent.parent.parent, Path(__file__).parent.parent.parent.parent, Path.cwd()]:
    env_path = root / '.env'
    if env_path.exists():
        dotenv_path = env_path
        break
if dotenv_path is None:
    dotenv_path = Path.cwd() / '.env'

load_dotenv(dotenv_path=dotenv_path, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
NEO4J_URI    = os.getenv("NEO4J_URI")
NEO4J_USER   = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def validate():
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not NEO4J_URI:
        missing.append("NEO4J_URI")
    if not NEO4J_USER:
        missing.append("NEO4J_USER")
    if not NEO4J_PASSWORD:
        missing.append("NEO4J_PASSWORD")
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")