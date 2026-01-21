import json
from pathlib import Path

def migrate(path):
    for file in Path(path).glob('**/*.json'):
        with open(file, 'r') as f:
            data = json.load(f)
        print(data)
        if "trains" in data:
            for train in data["trains"]:
                if isinstance(train["movements"], list):
                    train["movements"] = train["movements"][0]
            with open(file, 'w') as f:
                json.dump(data, f, indent=4)

if __name__ == '__main__':
    migrate("../tests")