from ast import literal_eval
from collections import defaultdict


from utils import markup_inline_keyboard, Config, stringify_dungeon_room, map_directions
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
        kwargs['info'] = {'username': chat.message['chat'].get('username'), 'dungeon_room': 'gabbia'}
        await log_user_action(chat, **kwargs)


async def stats_button_reply_phase1(chat, **_):
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
    markup = markup_inline_keyboard([dungeon_nums[i:i+3] for i in range(0, len(dungeon_nums), 3)], json=False)
    await chat.edit_text(chat.message.get('message_id'), 'Qual è il numero del dungeon?')
    await chat.edit_reply_markup(chat.message.get('message_id'), markup)


async def stats_choice_phase2(chat, **kwargs):
    dungeon, num = kwargs.get('match').group(1).split(':')
    redis = kwargs.get('redis')
    dungeon_map = literal_eval(await redis.get(f'map:{dungeon} {num}'))
    counter = defaultdict(int)
    for level in dungeon_map:
        for room in level:
            counter[room] += 1
    tot_rooms = len(dungeon_map) * 3
    percent_completed = round(((tot_rooms - counter.get('')) / tot_rooms) * 100, 2)
    reply = f"{dungeon} {num}\nPercentuale completamento {percent_completed}%\nMonete: {counter.get('monete') or 0}\n" \
            f"Spade: {counter.get('spada') or 0}\nAsce: {counter.get('ascia') or 0}\n" \
            f"Mattonelle: {counter.get('mattonella') or 0}\nStanze vuote: {counter.get('stanza vuota') or 0}\n"
    await chat.edit_text(chat.message.get('message_id'), reply)


async def map_next(chat, **kwargs):
    dungeon, start, end, scroll_direction = kwargs.get('match').group(1).split(':')
    start, end = int(start), int(end)
    redis = kwargs.get('redis')
    dungeon_map = literal_eval(await redis.get(f'map:{dungeon}'))

    if scroll_direction == 'down':
        start += 5
        end += 5
        if end > len(dungeon_map):
            start = 0
            end = 5
        dungeon_map = dungeon_map[start:end]
    else:
        start -= 5
        end -= 5
        if start < 0:
            end = len(dungeon_map)
            start = end - 5
        dungeon_map = dungeon_map[start:end]
    markup = map_directions(dungeon, start, end, json=False)
    printable_map = dungeon + '\n\n'
    for i, level in enumerate(dungeon_map, start):
        printable_map += stringify_dungeon_room(i+1, *level)
    await chat.edit_text(chat.message.get('message_id'), printable_map, parse_mode='Markdown')
    await chat.edit_reply_markup(chat.message.get('message_id'), markup)


async def dungeon_exchange(chat, **kwargs):
    redis = kwargs.get('redis')
    sender, receiver, dungeon = kwargs.get('match').group(1).split(':')
    await redis.hset(sender, 'active_dungeon', '')
    await chat.edit_text(
        chat.message.get('message_id'),
        f'Sei uscito da {dungeon} e ho mandato una richiesta a {receiver}')
    receiver_user_id = await redis.hget(receiver, 'user_id')
    chat.id = receiver_user_id
    markup = markup_inline_keyboard(
        [[('si', f'confirmtradeclick-si:{receiver}:{dungeon}'), ('no', f'confirmtradeclick-no:{receiver}:{dungeon}')]])
    await chat.send_text(f'{sender} dice di averti messo in {dungeon}, confermi?', reply_markup=markup)


async def confirm_trade(chat, **kwargs):
    redis = kwargs.get('redis')
    response, receiver, dungeon = kwargs.get('match').group(1).split(':')
    if response == 'si':
        await redis.hset(receiver, 'active_dungeon', dungeon)
        await chat.edit_text(chat.message.get('message_id'), f'Sei stato aggiunto al dungeon {dungeon}')
    else:
        await chat.edit_text( chat.message.get('message_id'), 'Ok non sei stato aggiunto!')