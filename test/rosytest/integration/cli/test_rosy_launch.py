from rosytest.integration.cli.utils import rosy_cli
from rosytest.util import REPO_ROOT


def test_rosy_launch():
    launch_yaml = str(REPO_ROOT / "src" / "rosy" / "demo" / "launch.yaml")
    with rosy_cli("launch", launch_yaml) as launch_proc:
        launch_proc.expect_exact(
            [
                f"[rosy launch] Using config: {launch_yaml}\n",
                "[rosy launch] Press Ctrl+C to stop all nodes.",
                # Message from demo topic_listener node indicating it received a message
                'Received "hello world" on topic=some-topic',
            ]
        )
