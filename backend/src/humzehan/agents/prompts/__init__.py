"""Prompt files for the agent nodes (one Markdown file per node)."""

import re
from functools import cache
from importlib.resources import files


@cache
def load_prompt(name: str) -> str:
    """Return the text of ``agents/prompts/<name>.md``."""
    return files("humzehan.agents.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")


@cache
def style_rules(mode: str) -> str:
    """The "## <Style> style rules" section of a transform prompt (shared with the checker)."""
    pattern = r"^## [^\n]* style rules\n.*?(?=^## |\Z)"
    match = re.search(pattern, load_prompt(mode), re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(f"No style rules section in {mode}.md")
    return match.group(0).strip()


@cache
def prompt_section(name: str, heading: str) -> str:
    """The "## <heading>" section (heading line included) of ``agents/prompts/<name>.md``."""
    pattern = rf"^## {re.escape(heading)}\n.*?(?=^## |\Z)"
    match = re.search(pattern, load_prompt(name), re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(f"No '## {heading}' section in {name}.md")
    return match.group(0).strip()
