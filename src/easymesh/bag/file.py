import pickle
from datetime import datetime
from pathlib import Path
from typing import Iterable

from easymesh.types import Data, Topic

Message = tuple[datetime, Topic, Data]


def get_bag_file_messages(bag_file_path: Path) -> Iterable[Message]:
    with open(bag_file_path, 'rb') as bag_file:
        while True:
            try:
                yield pickle.load(bag_file)
            except EOFError:
                break
