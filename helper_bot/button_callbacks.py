from ast import literal_eval
from collections import defaultdict
from logging import getLogger

from .utils import markup_inline_keyboard
from .settings import Dungeon

logger = getLogger(__name__)


async def stats_button_reply_phase1(chat, **_):
    return await chat.send_text('Di quale tipologia dungeon vuoi le statistiche?', reply_markup=Dungeon.MARKUP)


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
    # dungeon_deadline = await redis.hget('dungeon_deadlines', f'{dungeon} {num}')
    percent_completed = round(((tot_rooms - (counter.get('') or 0)) / tot_rooms) * 100, 2)
    reply = f"{dungeon} {num}\nPercentuale completamento {percent_completed}%\nMonete: {counter.get('monete') or 0}\n" \
            f"Spade: {counter.get('spada') or 0}\nAsce: {counter.get('ascia') or 0}\n" \
            f"Aiuta: {counter.get('aiuta') or 0}\nMattonelle: {counter.get('mattonella') or 0}\n" \
            f"Stanze vuote: {counter.get('stanza vuota') or 0}\n" \
            f"Fontana: {counter.get('fontana') or 0}\nIncisioni: {counter.get('incisioni') or 0}"
    await chat.send_text(reply)


async def map_next(chat, **kwargs):
    dungeon, start, end, scroll_direction, user = kwargs.get('match').group(1).split(':')
    start, end = int(start), int(end)
    redis = kwargs.get('redis')
    try:
        dungeon_map = literal_eval(await redis.get(f'map:{dungeon}'))
    except ValueError:
        logger.warning(f'mappa non trovata map:{dungeon}')
        return await chat.send_text("Non trovo piu questa mappa è possibile che qualcuno l' abbia archiviata")
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
    markup = Dungeon.map_directions(dungeon, start, end, user, json=False)
    printable_map = dungeon + '\n\n'
    for i, level in enumerate(dungeon_map, start):
        printable_map += Dungeon.stringify_room(
            i+1, *level, await redis.hgetall(f"custom_emojis:{user}") or Dungeon.EMOJIS)
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
    position = await redis.hget(sender, 'position')
    chat.id = receiver_user_id
    markup = markup_inline_keyboard([
        [('si', f'confirmtradeclick-si:{receiver}:{position}:{dungeon}'),
         ('no', f'confirmtradeclick-no:{receiver}:{position}:{dungeon}')]])
    await chat.send_text(f'{sender} dice di averti messo in {dungeon}, confermi?', reply_markup=markup)


async def confirm_trade(chat, **kwargs):
    redis = kwargs.get('redis')
    response, receiver, position, dungeon = kwargs.get('match').group(1).split(':')
    if response == 'si':
        await redis.hmset_dict(receiver, {'active_dungeon': dungeon, 'position': position})
        await chat.edit_text(chat.message.get('message_id'), f'Sei stato aggiunto al dungeon {dungeon}')
    else:
        await chat.edit_text(chat.message.get('message_id'), 'Ok non sei stato aggiunto!')
