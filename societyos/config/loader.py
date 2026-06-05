from pathlib import Path
import yaml
from .models import SocietyConfig


def load_config(path: str | Path) -> SocietyConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    raw = p.read_text(encoding="utf-8")
    data: dict = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a YAML mapping, got {type(data)}")
    society_block = data.pop("society", {})
    data.update(society_block)
    try:
        return SocietyConfig(**data)
    except Exception as exc:
        raise ValueError(f"Invalid society config in {p}:\n{exc}") from exc
