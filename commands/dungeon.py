from datetime import timedelta
from ast import literal_eval

from utils import Config, dungeon_len, stringify_dungeon_room, is_number, map_directions, ErrorReply
from deco import must_be_forwarded_message, must_have_active_dungeon, strict_args_num


@must_be_forwarded_message
async def set_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    dungeon_name = kwargs.get('match').group(1)
    if await redis.hget(info.get('username'), 'active_dungeon'):
        return await chat.reply('Errore!\nHai gia un dungeon attivo concludilo o scambialo con /quitdg')
    await redis.hmset_dict(info.get('username'),
                           {'active_dungeon': dungeon_name, 'position': 1})
    await redis.setex('dungeon:' + dungeon_name, int(timedelta(days=2, hours=7).total_seconds()), '')
    if not await redis.exists(f"map:{dungeon_name}"):
        await redis.set(f"map:{dungeon_name}", str([['']*3 for _ in range(dungeon_len(dungeon_name))]))
    await chat.reply(f'{dungeon_name} è il tuo dungeon attivo ora!')


@must_have_active_dungeon
async def close_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    args = info.get('args')
    sender = info.get('username')
    dungeon_name = await redis.hget(sender, 'active_dungeon')
    if len(args) == 1:
        receiver = args[0]
        if await redis.sismember(info.get('group'), receiver):
            await redis.hmset_dict(receiver, {'active_dungeon': dungeon_name, 'position': 1})
            await chat.reply(f"Hai scambiato {dungeon_name} con {receiver}")
        else:
            return await chat.reply(f"Errore!\n{receiver} non è nel tuo gruppo!")
    await redis.hset(sender, 'active_dungeon', '')
    await chat.reply(f'Sei uscito da {dungeon_name}')


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
    dungeon_room = dungeon_room if dungeon_room else Config.DUNGEONS_RE.get(match.group(0))
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
    if max_rooms != dungeon_len(active_dungeon):
        return await chat.reply('Oi mi stai mandando la stanza di un altro dungeon! Pirla!!!')
    return await redis.append(f"dungeon:{active_dungeon}", f"{sender},{chat.message.get('forward_date')},{position}:")


async def get_map(chat, **kwargs):
    redis = kwargs.get('redis')
    args = kwargs.get('info').get('args')
    active_dungeon = await redis.hget(kwargs.get('info').get('username'), 'active_dungeon')
    if len(args) == 2:
        name, num = args
        if name in Config.DUNGEONS_ACRONYMS:
            active_dungeon = Config.DUNGEONS_ACRONYMS.get(name)
        else:
            return chat.reply(f"Errore!\nLa sigla dungeon che mi ha mandato non esiste!\n"
                              f"Opzioni valide: {', '.join(Config.DUNGEONS_ACRONYMS.keys())}")
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
        active_dungeon + '\n\n' + ''.join([stringify_dungeon_room(i, *level) for i, level in enumerate(dungeon_map, 1)])
    markup = map_directions(active_dungeon, 0, 5)
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
    if position > dungeon_len(active_dungeon):
        return await chat.reply('Errore!\n La stanza richiesta è maggiore ')
    dungeon_map = literal_eval(await redis.get(f"map:{active_dungeon}"))
    await redis.hset(sender, 'position', position)
    return await chat.reply(stringify_dungeon_room(position, *dungeon_map[position-1]), parse_mode='Markdown')


@must_have_active_dungeon
async def get_current_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    await chat.reply(await redis.hget(sender, 'active_dungeon'))
