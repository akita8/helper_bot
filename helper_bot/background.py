from ast import literal_eval
from collections import defaultdict
from datetime import timedelta
from logging import getLogger

from .decorators import periodic, setup_coro

from helper_bot.settings import Dungeon, Url, BotConfig

logger = getLogger(__name__)


# @setup_coro
# @periodic(30)
# async def update_sales(bot, redis):
#     async with bot.session.get(Url.SHOPS) as s:
#         sales = await s.json()
#     for item in sales['res']:
#         key = f"sale:{item.get('item_id')}:{item.get('code')}"
#         value = f"{item.get('price')},{item.get('quantity')}"
#         await redis.setex(key, 15*60, value)


# @setup_coro
# @periodic(15)
# async def send_alert(redis):
#     async for _ in redis.iscan(match='sale:*'):
#         pass


@setup_coro
@periodic(3600)
async def update_group_members(bot, redis):
    for group in BotConfig.ALLOWED_GROUPS:
        await redis.delete(group)
        async with bot.session.get(Url.GROUP + group) as s:
            group_members = await s.json()
        for member in group_members['res']:
            await redis.sadd(group, member['nickname'])


@setup_coro
@periodic(30)
async def build_maps(bot, redis):
    async for key in redis.iscan(match='dungeon:*'):
        dungeon_name = key.split(':')[1]
        map_key = f'map:{dungeon_name}'
        try:
            dungeon_map = literal_eval(await redis.get(map_key))
        except ValueError:
            await redis.delete(key)
            logger.warning(f'mappa non trovata di {map_key}')
            continue
        dungeon_string = await redis.get(key)
        dungeon = []
        for line in dungeon_string.split(':')[:-1]:
            line = line.split(',')
            if line not in dungeon:
                dungeon.append(line)
        ordered_dungeon = defaultdict(list)
        for entry in sorted(dungeon, key=lambda x: x[1]):
            ordered_dungeon[entry[0]].append(entry[1:])
        for user, entries in ordered_dungeon.items():
            processed = []
            reply = ''
            for i, entry in enumerate(entries):
                event = entry[1]
                if event in Dungeon.ROOMS or 'mostro' in event:
                    if i >= 2 and entries[i - 1][1] in Dungeon.DIRECTIONS:
                        try:
                            number = int(entries[i - 2][1])
                            direction_emoji = entries[i - 1][1]
                            direction = Dungeon.DIRECTIONS[direction_emoji]
                            dungeon_map[number - 1][direction] = event
                            processed += [i, i-2, i-1]
                            reply += f'Hai aggiunto *{event}* alla stanza numero {number} direzione {direction_emoji}\n'
                        except ValueError:
                            continue
            if reply:
                id_ = await redis.hget(user, 'user_id')
                private_chat = bot.private(id_)
                await private_chat.send_text(reply, parse_mode='Markdown')
                new_position = number + 1
                if number < len(dungeon_map):
                    next_room = dungeon_map[number]
                    await redis.hset(user, 'position', new_position)
                    if any(next_room):
                        await private_chat.send_text(
                            Dungeon.stringify_room(new_position, *next_room, await redis.hgetall(f"custom_emojis:{user}") or Dungeon.EMOJIS),
                            parse_mode='Markdown')
            not_processed = [','.join([user] + entry) for i, entry in enumerate(entries) if i not in processed]
            dungeon_ttl = await redis.ttl(key)
            remaining = ':'.join(not_processed)
            await redis.setex(
                key,
                dungeon_ttl if dungeon_ttl > 1 else int(timedelta(days=2, hours=7).total_seconds()),
                remaining + ':' if remaining else '')
        map_ttl = await redis.ttl(map_key)
        await redis.setex(map_key, map_ttl if map_ttl > 1 else int(timedelta(days=7).total_seconds()), str(dungeon_map))
