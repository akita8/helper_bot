from ast import literal_eval
from datetime import timedelta, datetime

from helper_bot.decorators import must_be_forwarded_message, must_have_active_dungeon, strict_args_num

from helper_bot.settings import Emoji, ErrorReply, Dungeon
from helper_bot.utils import markup_inline_keyboard, is_number


@must_be_forwarded_message
async def set_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    dungeon_name = kwargs.get('match').group(1)
    if await redis.hget(info.get('username'), 'active_dungeon'):
        return await chat.reply('Errore!\nHai gia un dungeon attivo concludilo o scambialo con /quitdg')
    await redis.hmset_dict(info.get('username'),
                           {'active_dungeon': dungeon_name, 'position': 0})
    await redis.setex('dungeon:' + dungeon_name, int(timedelta(days=2, hours=7).total_seconds()), '')
    if not await redis.exists(f"map:{dungeon_name}"):
        await redis.set(f"map:{dungeon_name}", str([['']*3 for _ in range(Dungeon.length(dungeon_name))]))
    await chat.reply(f'{dungeon_name} è il tuo dungeon attivo ora!')


@must_have_active_dungeon
async def close_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    sender = info.get('username')
    active_dungeon = kwargs.get('active_dungeon')
    await redis.hset(sender, 'active_dungeon', '')
    await chat.reply(f'Sei uscito da {active_dungeon}')


@must_have_active_dungeon
async def trade_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    dungeon = kwargs.get('active_dungeon')
    group = info.get('group')
    sender = info.get('username')
    members = [
        (member, f"tradedgclick-{sender}:{member}:{dungeon}")
        for member in await redis.smembers(group) if member != sender]
    markup = markup_inline_keyboard([members[i:i+3] for i in range(0, len(members), 3)])
    return chat.send_text('A chi vuoi passare il tuo dungeon?', reply_markup=markup)


@must_be_forwarded_message
@must_have_active_dungeon
async def log_user_action(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    match = kwargs.get('match')
    sender = info.get('username')
    active_dungeon = kwargs.get('active_dungeon')
    await redis.hsetnx(sender, 'user_id', chat.message['chat'].get('id'))
    dungeon_room = info.get('dungeon_room')
    dungeon_room = dungeon_room if dungeon_room else Dungeon.RE.get(match.group(0))
    if dungeon_room == 'mostro':
        level_loc = chat.message['entities'][1]
        level = chat.message['text'][level_loc.get('offset'):level_loc.get('offset') + level_loc.get('length')]
        dungeon_room += ' ' + level
    time = str(int(chat.message.get('forward_date')) + 1)
    return await redis.append(f"dungeon:{active_dungeon}", f"{sender},{time},{dungeon_room}:")


@must_be_forwarded_message
@must_have_active_dungeon
async def log_user_direction(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    direction = kwargs.get('match').group(1)
    active_dungeon = kwargs.get('active_dungeon')
    return await redis.append(f"dungeon:{active_dungeon}", f"{sender},{chat.message.get('forward_date')},{direction}:")


@must_be_forwarded_message
@must_have_active_dungeon
async def log_user_position(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    position = kwargs.get('match').group(1)
    max_rooms = int(kwargs.get('match').group(2))
    active_dungeon = kwargs.get('active_dungeon')
    if max_rooms != Dungeon.length(active_dungeon):
        return await chat.reply('Oi mi stai mandando la stanza di un altro dungeon! Pirla!!!')
    return await redis.append(f"dungeon:{active_dungeon}", f"{sender},{chat.message.get('forward_date')},{position}:")


async def get_map(chat, **kwargs):
    redis = kwargs.get('redis')
    args = kwargs.get('info').get('args')
    active_dungeon = await redis.hget(kwargs.get('info').get('username'), 'active_dungeon')
    if len(args) == 2:
        name, num = args
        if name in Dungeon.ACRONYMS:
            active_dungeon = Dungeon.ACRONYMS.get(name)
        else:
            return chat.reply(f"Errore!\nLa sigla dungeon che mi ha mandato non esiste!\n"
                              f"Opzioni valide: {', '.join(Dungeon.ACRONYMS.keys())}")
        if is_number(num):
            active_dungeon += ' ' + num
        else:
            return chat.reply(f"Errore!\n{num} non è un numero!")
    elif not active_dungeon:
        return await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)
    map_string = await redis.get(f'map:{active_dungeon}')
    if not map_string:
        return await chat.reply('La mappa del dungeon che hai richiesto non esiste!')
    dungeon_map = literal_eval(map_string)[:5]
    printable_map = \
        active_dungeon + '\n\n' + ''.join([Dungeon.stringify_room(i, *level) for i, level in enumerate(dungeon_map, 1)])
    markup = Dungeon.map_directions(active_dungeon, 0, 5)
    return await chat.send_text(printable_map, reply_markup=markup, parse_mode='Markdown')


@must_have_active_dungeon
@strict_args_num('{}<=1')
async def next_room(chat, **kwargs):
    redis = kwargs.get('redis')
    active_dungeon = kwargs.get('active_dungeon')
    info = kwargs.get('info')
    sender = info.get('username')
    arg = info.get('args')
    try:
        position = int(await redis.hget(sender, 'position')) + 1 if not arg else int(arg[0])
    except ValueError:
        return chat.reply("Errore!\n L'argomento del comando deve essere un numero!")
    if position > Dungeon.length(active_dungeon):
        return await chat.reply('Errore!\n La stanza richiesta è maggiore ')
    dungeon_map = literal_eval(await redis.get(f"map:{active_dungeon}"))
    await redis.hset(sender, 'position', position)
    return await chat.reply(Dungeon.stringify_room(position, *dungeon_map[position-1]), parse_mode='Markdown')


@must_have_active_dungeon
async def get_current_dungeon(chat, **kwargs):
    await chat.reply(kwargs.get('active_dungeon'))


@strict_args_num('{}==2')
async def expire_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    dungeon_acronym, num = kwargs.get('info').get('args')
    dungeon_name = Dungeon.ACRONYMS.get(dungeon_acronym)
    if dungeon_name and is_number(num):
        map_key, dungeon_key = f"map:{dungeon_name} {num}", f"dungeon:{dungeon_name} {num}"
        map_string = await redis.get(map_key)
        if map_string and isinstance(map_string, str):
            await redis.delete(map_key)
            await redis.delete(dungeon_key)
            await redis.hset('cancelled_dungeons_maps', map_key + ':' + str(datetime.now()), map_string)
            await chat.reply(f'Hai cancellato la mappa del dungeon {dungeon_name}')
        else:
            chat.reply(f'Errore!\nNon ho trovato il dungeon {dungeon_name} nel database!')
    else:
        return chat.reply(f"Errore!\nLa sigla dungeon che mi ha mandato non esiste o il numero non è valido!\n"
                          f"Opzioni valide: {', '.join(Dungeon.ACRONYMS.keys())}")


@must_have_active_dungeon
async def map_todo(chat, **kwargs):
    def completion_visualization(level, num):
        vis = f"{num if len(num)==2 else '0'+num}. "
        for direction in level:
            vis += Dungeon.EMOJIS.get(direction)
        return vis
    redis = kwargs.get('redis')
    active_dungeon = kwargs.get('active_dungeon')
    dungeon_map = literal_eval(await redis.get(f"map:{active_dungeon}"))
    printable_map = \
        active_dungeon + '\n\n' + \
        '\n'.join([completion_visualization(level, str(i+1)) for i, level in enumerate(dungeon_map)])
    await chat.reply(printable_map)


@must_be_forwarded_message
async def set_expire_date(chat, **kwargs):
    # TODO not working (problem in the regex)
    try:
        redis = kwargs.get('redis')
        message = chat.message['text'].split('\n')
        dungeon_name = message[0]
        raw_deadline = message[3].split(' ')
        dungeon_deadline = f'{raw_deadline[2]}-{raw_deadline[4]}'
        await redis.hset('dungeon_deadlines', dungeon_name, dungeon_deadline)
        await chat.reply(f'Ok ho impostato {dungeon_deadline} per {dungeon_name} come data di crollo')
    except IndexError:
        return