from helper_bot.utils import is_number, is_time, markup_inline_keyboard


def test_is_number():
    assert not is_number('string')
    assert is_number(1)


def test_is_time():
    pass


def test_markup_inline_keyboard():
    pass