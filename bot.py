import asyncio
import logging

from datetime import datetime


import aioredis
import emoji

from aiotg import Bot


with open('token.txt') as f:
    token = f.read()

bot = Bot(token, name='steephighe')
redis = None

ALLOWED_GROUPS = ('DDO', 'ACDC')
GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'


def check_group(name):
    for g in ALLOWED_GROUPS:
        if g in name:
            return g
    return False


@bot.command(fr'/setboss@{bot.name}')
async def setboss(chat, match):
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice'):
        return await chat.reply('Errore!\nSintassi corretta: /setboss@steephighe_bot boss deadline')
    try:
        datetime.strptime(msg[2], '%H:%M')
    except ValueError:
        return await chat.reply('Errore!\nOrario invalido!')
    group = check_group(chat.message['chat']['title'])
    if group:
        async with bot.session.get(GROUP_URL+group) as s:
            group_members = await s.json()
        fields = {**{v['nickname']: "" for v in group_members['res']}, **{"boss": msg[1], "deadline": msg[2]}}
        await redis.hmset_dict(f'boss:{group}', fields)
        return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


@bot.command(fr'/bottalist@{bot.name}')
@bot.command(fr'/bottalistag@{bot.name}')
async def scalata(chat, match):
    group = check_group(chat.message['chat']['title'])
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

@bot.command(fr'/botta@{bot.name}')
async def botta(chat, match):
    group = check_group(chat.message['chat']['title'])
    sender = chat.sender['username']
    msg = chat.message['text'].split(' ')
    if await redis.hgetall(f'boss:{group}'):
        if len(msg) == 1:
            await redis.hset(f'boss:{group}', sender, 'ok')
            return await chat.reply(f'{sender} ha dato la botta!')
        elif len(msg) == 2:
            try:
                datetime.strptime(msg[1], '%H:%M')
                await redis.hset(f'boss:{group}', chat.sender['username'], msg[1])
                return await chat.reply(f'{sender} darà la botta alle {msg[1]}!')
            except ValueError:
                return await chat.reply('Errore!\nOrario invalido!')
        else:
            return await chat.reply('Errore!\nSintassi corretta: /botta@steephighe_bot orario_botta(opzionale)')
    else:
        chat.reply('Errore!\nNon ho trovato boss impostati --> /setboss@steephighe_bot.')


async def main():
    global redis
    redis = await aioredis.create_redis(('localhost', 6379), encoding="utf-8")
    await bot.loop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        bot.stop()
