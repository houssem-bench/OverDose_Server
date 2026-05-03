"""
Structured logging with Rich for colorful terminal output.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "agent": "bold magenta",
    "scraper": "bold blue",
    "mcp": "bold cyan",
})

console = Console(theme=custom_theme)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger with Rich handler."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def log_agent_action(agent_name: str, action: str, details: str = ""):
    """Log an agent action with colored output."""
    logger = get_logger("overdose")
    logger.info(f"[agent]🤖 {agent_name}[/agent] -> {action} {details}")


def log_scraper_action(source: str, action: str, count: int = 0):
    """Log a scraper action."""
    logger = get_logger("overdose")
    logger.info(f"[scraper]🔍 {source}[/scraper] -> {action} ({count} items)")


def log_mcp_call(tool: str, params: dict):
    """Log an MCP tool call."""
    logger = get_logger("overdose")
    logger.info(f"[mcp]⚡ MCP[/mcp] -> {tool}({params})")
