from __future__ import annotations

from pathlib import Path
import tomllib

from setuptools import setup

_RELEASE_DESCRIPTOR = Path(__file__).parent / "src/chromatix_next/release.toml"
_RELEASE = tomllib.loads(
    _RELEASE_DESCRIPTOR.read_text(encoding="utf-8")
)["release"]

setup(version=_RELEASE["version"])
