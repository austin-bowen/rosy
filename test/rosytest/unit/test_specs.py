import pytest

from rosy.specs import NodeId, NodeUUID


@pytest.mark.parametrize(
    "name, expected_name",
    [
        ("node1", "node1"),
        ("node 2", "'node 2'"),
    ],
)
def test_NodeId_str(name: str, expected_name: str):
    node_id = NodeId(
        name=name,
        hostname="hostname",
        uuid=NodeUUID("beef0000-0000-0000-0000-000000000000"),
    )
    assert str(node_id) == f"{expected_name}@hostname (beef)"
