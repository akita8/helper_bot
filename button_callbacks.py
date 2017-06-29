from utils import markup_inline_keyboard, Config
from commands.riddle_solvers import namesolver
from commands.dungeon import log_user_action


async def gabbia_buttons_reply(chat, **_):
    markup = markup_inline_keyboard([
        [('risolvi', 'gabbiaclick-solver'),
         ('mappa', f"gabbiaclick-{chat.message.get('forward_date')}")]])
    await chat.send_text(chat.message['text'], reply_markup=markup)


async def gabbia_choice(chat, **kwargs):
    match = kwargs.get('match')
    if match.group(1) == 'solver':
        await chat.edit_text(chat.message.get('message_id'), 'Ok adesso lo risolvo!')
        await namesolver(chat, **kwargs)
    else:
        chat.message['forward_date'] = match.group(1)
        await chat.edit_text(chat.message.get('message_id'), 'Ok lo ho aggiunto al tuo dungeon!')
        kwargs['info'] = {**kwargs['info'], 'username': chat.message['chat'].get('username'), 'dungeon_room': 'gabbia'}
        await log_user_action(chat, **kwargs)


async def maps_button_reply_phase1(chat, **kwargs):
    return await chat.send_text('Di quale dungeon cerchi mappe?', reply_markup=Config.DUNGEON_MARKUP)


async def maps_choice_phase1(chat, **kwargs):
    match = kwargs.get('match')
    await chat.edit_text(chat.message.get('message_id'), '')
