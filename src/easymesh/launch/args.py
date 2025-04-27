from dataclasses import dataclass
from typing import Union


@dataclass
class ProcessArgs:
    args: Union[str, list[str]]

    def append(self, arg: str) -> None:
        if isinstance(self.args, str):
            if not arg:
                arg = '""'
            elif ' ' in arg and not (arg[0] == arg[-1] == '"'):
                arg = f'"{arg}"'

            self.args = f'{self.args} {arg}'
        else:
            self.args.append(arg)

    def extend(self, args: list[str]) -> None:
        for arg in args:
            self.append(arg)
