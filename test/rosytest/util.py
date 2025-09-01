from pathlib import Path
from unittest.mock import create_autospec

from rosy.specs import IpConnectionSpec, MeshNodeSpec, NodeId

REPO_ROOT = Path(__file__).parent.parent.parent

assert REPO_ROOT.name == "rosy"


def mock_node_spec(name: str = "node"):
    node = create_autospec(MeshNodeSpec)
    node.id = NodeId(name)
    node.connection_specs = [create_autospec(IpConnectionSpec)]
    return node
