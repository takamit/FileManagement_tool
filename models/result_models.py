from dataclasses import dataclass


@dataclass
class CompareResult:
    category: str
    target_path: str
    compare_path: str
