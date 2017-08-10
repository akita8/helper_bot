import datetime
from json import dumps


def markup_inline_keyboard(buttons, json=True):
    markup = {
        'type': 'InlineKeyboardMarkup',
        'inline_keyboard': []}
    for button_level in buttons:
        formatted_level = []
        for button in button_level:
            text, cb_data = button
            formatted_level.append({'type': 'InlineKeyboardButton', 'text': text, 'callback_data': cb_data})
        markup['inline_keyboard'].append(formatted_level)
    if json:
        return dumps(markup)
    return markup


def is_time(time_string, date_format='%H:%M'):
    try:
        datetime.datetime.strptime(time_string.replace('.', ':'), date_format)
    except ValueError:
        return False
    return True


def is_number(number):
    try:
        int(number)
    except ValueError:
        return False
    return True
