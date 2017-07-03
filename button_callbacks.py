from ast import literal_eval
from collections import defaultdict

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


async def stats_button_reply_phase1(chat, **kwargs):
    return await chat.send_text('Di quale tipologia dungeon vuoi le statistiche?', reply_markup=Config.DUNGEON_MARKUP)


async def stats_choice_phase1(chat, **kwargs):
    dungeon = kwargs.get('match').group(1)
    redis = kwargs.get('redis')
    dungeon_nums = []
    async for key in redis.iscan(match=f'map:{dungeon}*'):
        num = key.split(' ')[-1]
        dungeon_nums.append((num, f"stats2click-{dungeon}:{num}"))
    if not dungeon_nums:
        return await kwargs.get('cb_query').answer(text='Non ho dungeon attivi di questa tipologia!')
    markup = markup_inline_keyboard([dungeon_nums[i:i+3] for i in range(0, len(dungeon_nums), 3)])
    await chat.send_text('Qual è il numero del dungeon?', reply_markup=markup)


async def stats_choice_phase2(chat, **kwargs):
    dungeon, num = kwargs.get('match').group(1).split(':')
    redis = kwargs.get('redis')
    dungeon_map = literal_eval(await redis.hget(f'map:{dungeon} {num}', 'string'))
    counter = defaultdict(int)
    for level in dungeon_map:
        for room in level:
            counter[room] += 1
    tot_rooms = len(dungeon_map) * 3
    percent_completed = round(((tot_rooms - counter.get('')) / tot_rooms) * 100, 2)
    reply = f"{dungeon} {num}\nPercentuale completamento {percent_completed}%\nMonete: {counter.get('monete') or 0}\n" \
            f"Spade: {counter.get('spada') or 0}\nAsce: {counter.get('ascia') or 0}\n" \
            f"Mattonelle: {counter.get('mattonella') or 0}\nStaze vuote: {counter.get('stanza vuota') or 0}\n"
    await chat.edit_text(chat.message.get('message_id'), reply)
