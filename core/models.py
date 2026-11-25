from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SeparationResult:
    vocals: Path
    instrumental: Path


@dataclass(frozen=True)
class AnalysisResult:
    bpm: float
    key: str
    key_confidence: float
