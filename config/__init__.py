import os
from pathlib import Path
from dotenv import load_dotenv

# Debug: print the current file location
print(f"Config file location: {__file__}")

# Compute possible project root paths
possible_roots = [
    Path(__file__).parent.parent.parent,  # go up 3 levels
    Path(__file__).parent.parent.parent.parent,  # go up 4 levels
    Path.cwd(),  # current working directory
]

for i, root in enumerate(possible_roots):
    env_path = root / '.env'
    print(f"Option {i}: {env_path.resolve()} exists? {env_path.exists()}")
    if env_path.exists():
        dotenv_path = env_path
        break
else:
    # If none found, use current working directory (where manage.py is run from)
    dotenv_path = Path.cwd() / '.env'
    print(f"Using fallback: {dotenv_path.resolve()}")

load_dotenv(dotenv_path=dotenv_path, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
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
    print("✅ Configuration validated")