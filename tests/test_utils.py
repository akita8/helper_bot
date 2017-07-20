from helper_bot.utils import is_number, is_time, markup_inline_keyboard


def test_is_number():
    assert not is_number('string')
    assert is_number(1)


def test_is_time():
    assert is_time('23:56')
    assert is_time('01/01/2000 00:00', date_format='%d/%m/%Y %H:%M')
    assert not is_time('25:67')
    assert not is_time('test')


def test_markup_inline_keyboard():
    test_markup = markup_inline_keyboard([
        [('test1', 'callbacktest1'), ('test2', 'callbacktest2')], [('test3', 'callbacktest3')]], json=False)
    assert test_markup.get('type') == 'InlineKeyboardMarkup'
    assert isinstance(test_markup.get('inline_keyboard'), list)
    assert len(test_markup.get('inline_keyboard')) == 2
    assert len(test_markup.get('inline_keyboard')[0]) == 2
    assert len(test_markup.get('inline_keyboard')[1]) == 1
    assert test_markup.get('inline_keyboard')[0][0].get('type') == 'InlineKeyboardButton'
    assert test_markup.get('inline_keyboard')[1][0].get('text') == 'test3'
    assert test_markup.get('inline_keyboard')[1][0].get('callback_data') == 'callbacktest3'
    test_markup_json = markup_inline_keyboard([
        [('test1', 'callbacktest1'), ('test2', 'callbacktest2')], [('test3', 'callbacktest3')]])
    assert isinstance(test_markup_json, str)