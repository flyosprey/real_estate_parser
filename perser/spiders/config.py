import json
from pathlib import Path


__root = Path(__file__).parent

with open(__root / "permit_numbers.json", 'r') as file:
    PermitNumbers = json.loads(file.read())["permit_numbers"]

