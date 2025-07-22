import pytest

from rosy.launch.args import ProcessArgs, quote_arg


class TestProcessArgs:
    def test_append_with_list_args(self):
        args = ProcessArgs(['foo', 'bar'])
        args.append('b a z')
        assert args.args == ['foo', 'bar', 'b a z']

    def test_append_with_str_args(self):
        args = ProcessArgs('foo bar')
        args.append('b a z')
        assert args.args == 'foo bar "b a z"'

    def test_extend_with_list_args(self):
        args = ProcessArgs(['foo', 'bar'])
        args.extend(['b a z', 'qux'])
        assert args.args == ['foo', 'bar', 'b a z', 'qux']

    def test_extend_with_str_args(self):
        args = ProcessArgs('foo bar')
        args.extend(['b a z', 'qux'])
        assert args.args == 'foo bar "b a z" qux'


@pytest.mark.parametrize('arg,expected', [
    ('', '""'),
    ('foo', 'foo'),
    ('foo bar', '"foo bar"'),
    ('"foo bar"', '"foo bar"'),
])
def test_quote_arg(arg, expected):
    assert quote_arg(arg) == expected
