import asyncio
import configparser
import logging

from datetime import datetime

import aioredis
import emoji

from aiotg import Bot


config = configparser.read('config.ini')

bot = Bot(config['BOT']['token'], name=config['BOT']['name'])
redis = None

ALLOWED_GROUPS = config['BOT']['allowed groups'].split(',')
GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'


def check_group(name):
    for g in ALLOWED_GROUPS:
        if g in name:
            return g
    return False


async def is_allowed_member(username):
    keys = await redis.keys('boss:*')
    for key in keys:
        if username in await redis.hgetall(key):
            return key.split(':')[1]
    return None


async def get_group(command, private, chat):
    if command == private and not chat.is_group():
        group = await is_allowed_member(chat.sender['username'])
        if not group:
            await chat.reply('Errore!\nNon sei in nessuno gruppo scalata!')
            return None
    else:
        group = check_group(chat.message['chat']['title'])
    return group


@bot.command(fr'/setboss@{bot.name}')
async def setboss(chat, match):
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice'):
        return await chat.reply('Errore!\nSintassi corretta: /setboss@steephighe_bot boss deadline')
    try:
        datetime.strptime(msg[2].replace('.', ':'), '%H:%M')
    except ValueError:
        return await chat.reply('Errore!\nOrario invalido!')
    group = check_group(chat.message['chat']['title'])
    if group:
        async with bot.session.get(GROUP_URL+group) as s:
            group_members = await s.json()
        fields = {**{v['nickname']: "" for v in group_members['res']}, **{"boss": msg[1], "deadline": msg[2]}}
        await redis.hmset_dict(f'boss:{group}', fields)
        return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


@bot.command(r'/bottalist')
@bot.command(fr'/bottalist@{bot.name}')
@bot.command(fr'/bottalistag@{bot.name}')
async def bottalist(chat, match):
    group = await get_group(match.group(0), '/bottalist', chat)
    if group:
        rv = await redis.hgetall(f'boss:{group}')
        if rv:
            boss = rv.pop('boss').capitalize()
            deadline = rv.pop('deadline')
            formatted = f'{boss} {deadline}\n\n'
            negative = emoji.emojize(':x:', use_aliases=True)
            positive = emoji.emojize(':white_check_mark:', use_aliases=True)
            for username, status in rv.items():
                em = positive if status == 'ok' else status if status else negative
                if match.group(0) == f'/bottalistag@{bot.name}':
                    formatted += f'@{username}: {em}\n' if not status else f'{username}: {em}\n'
                else:
                    formatted += f'{username}: {em}\n'
            return await chat.send_text(formatted)
        else:
            chat.reply('Errore!\nNon ho trovato boss impostati --> /setboss@steephighe_bot.')


@bot.command(r'/botta')
@bot.command(fr'/botta@{bot.name}')
async def botta(chat, match):
    print(chat.message)
    group = await get_group(match.group(0), '/botta', chat)
    if group:
        sender = chat.sender['username']
        msg = chat.message['text'].split(' ')
        if await redis.hgetall(f'boss:{group}'):
            if len(msg) == 1:
                await redis.hset(f'boss:{group}', sender, 'ok')
                return await chat.reply(f'{sender} ha dato la botta!')
            elif len(msg) == 2:
                try:
                    datetime.strptime(msg[1].replace('.', ':'), '%H:%M')
                    await redis.hset(f'boss:{group}', sender, msg[1])
                    return await chat.reply(f'{sender} darà la botta alle {msg[1]}!')
                except ValueError:
                    return await chat.reply('Errore!\nOrario invalido!')
            else:
                return await chat.reply('Errore!\nSintassi corretta: /botta@steephighe_bot orario_botta(opzionale)')
        else:
            chat.reply('Errore!\nNon ho trovato boss impostati --> /setboss@steephighe_bot.')


async def redis_connection():
    global redis
    redis = await aioredis.create_redis(('localhost', 6379), encoding="utf-8")


async def update_group_members():
    await asyncio.sleep(0.01)
    while True:
        for group in ALLOWED_GROUPS:
            async with bot.session.get(GROUP_URL+group) as s:
                group_members = await s.json()
            fields = {v['nickname']: "" for v in group_members['res']}
            await redis.hmset_dict(f'boss:{group}', fields)
        await asyncio.sleep(10)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(
            redis_connection(),
            #  update_group_members(),
            bot.loop()
        ))
    except KeyboardInterrupt:
        bot.stop()
