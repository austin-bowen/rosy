from typing import NamedTuple

from rosy.node.types import Args, KWArgs
from rosy.types import Topic


class TopicMessage(NamedTuple):
    topic: Topic
    args: Args
    kwargs: KWArgs
