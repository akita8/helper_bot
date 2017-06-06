import asyncio
import configparser
import logging

from datetime import datetime

import aioredis
import emoji

from aiotg import Bot


config = configparser.ConfigParser()
config.read('config.ini')

bot = Bot(config['BOT']['token'], name=config['BOT']['name'])
redis = None

logger = logging.getLogger('helper_bot')

ALLOWED_GROUPS = config['BOT']['allowed groups'].split(',')
GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
UNSET_BOSS_TEXT = f'Errore!\nNon ho trovato boss impostati --> /setboss@{bot.name}.'


def check_group(name):
    for g in ALLOWED_GROUPS:
        if g in name:
            return g
    return False


async def is_member(username, groups=ALLOWED_GROUPS):
    for g in groups:
        if await redis.sismember(g, username):
            return g


async def get_group(command, chat, private_command=''):
    if command == private_command and not chat.is_group():
        group = await is_member(chat.sender['username'])
        if not group:
            await chat.reply('Questo è un bot per uso privato mi dispiace non sei autorizzato')
            return
    else:
        group = check_group(chat.message['chat']['title'])
    return group


@bot.command(fr'/setboss@{bot.name}')
async def setboss(chat, match):
    group = await get_group(match.group(0), chat)
    if group:
        msg = chat.message['text'].split(' ')
        if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice'):
            return await chat.reply(f'Errore!\nSintassi corretta: /setboss@{bot.name} titano(o fenice) deadline')
        try:
            datetime.strptime(msg[2].replace('.', ':'), '%H:%M')
        except ValueError:
            return await chat.reply('Errore!\nOrario invalido!')
        group_members = await redis.smembers(group)
        fields = {**{member: "" for member in group_members}, **{"boss": msg[1], "deadline": msg[2]}}
        await redis.hmset_dict(f'boss:{group}', fields)
        return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


@bot.command(r'/bottalist')
@bot.command(fr'/bottalist@{bot.name}')
@bot.command(fr'/bottalistag@{bot.name}')
async def bottalist(chat, match):
    #  print(await chat.get_chat_administrators())
    group = await get_group(match.group(0), chat, '/bottalist')
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
            chat.reply(UNSET_BOSS_TEXT)


@bot.command(r'/unbotta')
async def joke(chat, match):
    async with bot.session.get('http://ron-swanson-quotes.herokuapp.com/v2/quotes') as s:
        quote = await s.json()
        await chat.reply(quote[0])


@bot.command(r'/botta')
@bot.command(fr'/botta@{bot.name}')
async def botta(chat, match):
    group = await get_group(match.group(0), chat, '/botta')
    if group:
        sender = chat.sender['username']
        msg = chat.message['text'].split(' ')
        success_text = f'{sender} ha dato la botta!'
        boss_list = await redis.hgetall(f'boss:{group}')
        if boss_list:
            if sender not in await redis.smembers(group):
                return await chat.reply('Uè pistola! Sei nella chat sbagliata!')
            if len(msg) == 1:
                await redis.hset(f'boss:{group}', sender, 'ok')
                return await chat.reply(success_text)
            elif len(msg) == 2:
                try:
                    datetime.strptime(msg[1].replace('.', ':'), '%H:%M')
                    await redis.hset(f'boss:{group}', sender, msg[1])
                    return await chat.reply(f'{sender} darà la botta alle {msg[1]}!')
                except ValueError:
                    admin_list_raw = await chat.get_chat_administrators()
                    admin_list = [admin['user']['username'] for admin in admin_list_raw['result']]
                    if sender in admin_list and msg[1] in boss_list:
                        await redis.hset(f'boss:{group}', msg[1], 'ok')
                        return await chat.reply(f'{msg[1]} ha dato la botta!')
                    elif len(msg[1]) == 1:
                        await redis.hset(f'boss:{group}', sender, msg[1])
                        return await chat.reply(success_text)
                    return await chat.reply('Errore!\nOrario invalido!')
            else:
                return await chat.reply(f'Errore!\nSintassi corretta: /botta@{bot.name} orario_botta(opzionale)')
        else:
            chat.reply(UNSET_BOSS_TEXT)


async def redis_connection():
    global redis
    logger.info('creating redis connection')
    redis = await aioredis.create_redis(('localhost', 6379), encoding="utf-8")


async def update_group_members():
    await asyncio.sleep(0.01)
    logger.info('starting members update coro')
    while True:
        for group in ALLOWED_GROUPS:
            async with bot.session.get(GROUP_URL+group) as s:
                group_members = await s.json()
            for member in group_members['res']:
                await redis.sadd(group, member['nickname'])
        logger.info('members list updated sleep for 6 hours')
        await asyncio.sleep(60*60*6)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(
            redis_connection(),
            update_group_members(),
            bot.loop()
        ))
    except KeyboardInterrupt:
        bot.stop()
