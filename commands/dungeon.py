from datetime import timedelta
from ast import literal_eval

from utils import Config, ErrorReply, dungeon_len
from deco import must_be_forwarded_message


@must_be_forwarded_message
async def set_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    dungeon_name = kwargs.get('match').group(1)
    if await redis.hget(info.get('username'), 'active_dungeon'):
        return await chat.reply('Errore!\nHai gia un dungeon attivo concludilo o scambialo con /quitdg')
    await redis.hmset_dict(info.get('username'),
                           {'active_dungeon': dungeon_name, 'user_id': chat.message['chat'].get('id')})
    await redis.setex('dungeon:' + dungeon_name, int(timedelta(days=2, hours=7).total_seconds()), '')
    await chat.reply(f'{dungeon_name} è il tuo dungeon attivo ora!')


async def close_dungeon(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    args = info.get('args')
    sender = info.get('username')
    dungeon_name = await redis.hget(sender, 'active_dungeon')
    if len(args) == 1:
        receiver = args[0]
        if await redis.sismember(info.get('group'), receiver):
            await redis.hset(receiver, 'active_dungeon', dungeon_name)
            await chat.reply(f"Hai scambiato {dungeon_name} con {receiver}")
        else:
            return await chat.reply(f"Errore!\nL'username {receiver} non esiste!")
    await redis.hset(sender, 'active_dungeon', '')
    await chat.reply(f'Sei uscito da {dungeon_name}')


@must_be_forwarded_message
async def log_user_action(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    match = kwargs.get('match')
    sender = info.get('username')
    active_dungeon = await redis.hget(sender, 'active_dungeon')
    if active_dungeon:
        dungeon_room = info.get('dungeon_room')
        dungeon_room = dungeon_room if dungeon_room else Config.DUNGEONS_RE.get(match.group(0))
        time = str(int(chat.message.get('forward_date')) + 1)
        return await redis.append(
            f"dungeon:{active_dungeon}",
            f"{sender},{time},{dungeon_room}:")
    await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)


@must_be_forwarded_message
async def log_user_direction(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    direction = kwargs.get('match').group(1)
    active_dungeon = await redis.hget(sender, 'active_dungeon')
    if active_dungeon:
        return await redis.append(
            f"dungeon:{active_dungeon}", f"{sender},{chat.message.get('forward_date')},{direction}:")
    await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)


@must_be_forwarded_message
async def log_user_position(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    position = kwargs.get('match').group(1)
    max_rooms = int(kwargs.get('match').group(2))
    active_dungeon = await redis.hget(sender, 'active_dungeon')
    if active_dungeon:
        if max_rooms != dungeon_len(active_dungeon):
            return await chat.reply('Oi mi stai mandando la stanza di un altro dungeon! Pirla!!!')
        return await redis.append(
            f"dungeon:{active_dungeon}", f"{sender},{chat.message.get('forward_date')},{position}:")
    await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)


async def get_map(chat, **kwargs):
    redis = kwargs.get('redis')
    sender = kwargs.get('info').get('username')
    active_dungeon = await redis.hget(sender, 'active_dungeon')
    if active_dungeon:
        dungeon_map = literal_eval(await redis.hget(f'map:{active_dungeon}', 'string'))
        printable_map = active_dungeon + '\n\n'
        for i, level in enumerate(dungeon_map, 1):
            left, up, right = level
            printable_map += f"Stanza: {i}\n{Config.ARROW_LEFT} --> {left} {Config.DUNGEONS_EMOJIS.get(left)}\n" \
                             f"{Config.ARROW_UP} --> {up} {Config.DUNGEONS_EMOJIS.get(up)}\n" \
                             f"{Config.ARROW_RIGHT} --> {right} {Config.DUNGEONS_EMOJIS.get(right)}\n\n"
        return await chat.reply(printable_map)
    await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)
