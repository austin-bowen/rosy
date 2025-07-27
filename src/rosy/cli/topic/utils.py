from collections.abc import Iterable


def print_args_and_kwargs(args: Iterable, kwargs: dict) -> None:
    if args:
        print('args:')
        for i, arg in enumerate(args):
            arg = arg_to_str(arg)
            print(f'  {i}: {arg}')

    if kwargs:
        print('kwargs:')
        for key, value in kwargs.items():
            value = arg_to_str(value)
            print(f'  {key}={value}')


def arg_to_str(arg) -> str:
    arg = repr(arg)

    if '\n' in arg:
        arg = f'```\n{arg}\n```'

    return arg
