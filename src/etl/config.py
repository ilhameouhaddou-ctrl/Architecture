from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    base_url: str
    timeout_seconds: int = 30


class PathsConfig(BaseModel):
    bronze_dir: Path
    silver_dir: Path
    gold_dir: Path


class ReferenceJob(BaseModel):
    name: str
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    output: str  # fichier JSON unique sous bronze_dir


class SeriesJob(BaseModel):
    name: str
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    output_dir: str  # sous-dossier sous bronze_dir, une page = un fichier


class BronzeConfig(BaseModel):
    references: list[ReferenceJob] = Field(default_factory=list)
    series: list[SeriesJob] = Field(default_factory=list)


class Settings(BaseModel):
    api: ApiConfig
    paths: PathsConfig
    bronze: BronzeConfig

    @classmethod
    def load(cls, path: Path | str = "config.yaml") -> "Settings":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
