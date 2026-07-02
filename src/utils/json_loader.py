import json
from pathlib import Path

def load_json(filename: str) -> dict:
    base_path = Path(__file__).parent.parent
    file_path = base_path / "mock_data" / filename

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
