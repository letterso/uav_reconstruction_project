from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "sampling": {
        "initial_fps": 5,
        "blur_threshold": 150,
        "parallax_threshold_px": 20,
        "output_dir": "frames",
        "fallback_fps": 30,
        "start_time": None,
        "end_time": None,
    },
    "features": {
        "type": "ORB",
        "max_features": 3000,
        "min_matches": 50,
    },
    "quality": {
        "use_ssim": False,
        "ssim_max": 0.98,
    },
}


def _deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path | None) -> Dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if path is None:
        return config

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}

    if not isinstance(user_config, dict):
        raise ValueError("Config root must be a mapping")

    return _deep_update(config, user_config)
