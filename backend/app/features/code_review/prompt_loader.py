"""Load versioned prompts from YAML files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptVersion(BaseModel):
    version: str
    description: str = ""
    system: str
    user_template: str = Field(description="Format string with a {diff} placeholder.")

    def format_user(self, diff: str) -> str:
        return self.user_template.format(diff=diff)


@lru_cache(maxsize=32)
def load_prompt(version: str) -> PromptVersion:
    path = PROMPTS_DIR / f"{version}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in PROMPTS_DIR.glob("*.yaml"))
        raise ValueError(f"Unknown prompt version: {version!r}. Available: {available}")
    with path.open() as f:
        data = yaml.safe_load(f)
    prompt = PromptVersion.model_validate(data)
    if prompt.version != version:
        raise ValueError(
            f"Prompt file {path.name} declares version={prompt.version!r} "
            f"but was requested as {version!r}"
        )
    return prompt


def list_versions() -> list[str]:
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.yaml"))
