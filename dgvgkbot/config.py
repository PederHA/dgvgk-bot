import yaml
from pathlib import Path

# String concatenation
def join(loader, node) -> str:
    seq = loader.construct_sequence(node)
    return ''.join(str(i) for i in seq)

# Parse value as Path
def path(loader, node) -> Path:
    seq = loader.construct_sequence(node)
    return Path('/'.join(str(i) for i in seq))


## register the tag handler
yaml.add_constructor('!join', join)
yaml.add_constructor('!path', path)


def load(path: str="config.yml") -> dict:
    with open(path, "r") as f:
        config = yaml.load(f)
    return config
