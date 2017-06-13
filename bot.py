import asyncio
import configparser
import functools
import logging
import os
import signal

from datetime import datetime

import aioredis
import emoji

from aiotg import Bot


logger = logging.getLogger('helper_bot')

config = configparser.ConfigParser()
try:
    config.read('config.ini') or config.read(os.environ['CONFIG_FILE'])
except KeyError:
    logger.error('config file NOT FOUND')
    exit()

bot = Bot(config['BOT']['token'], name=config['BOT']['name'])
redis = None

STARTUP_OFFSET = 1  # offset to allow the redis coro to establish the connection
ALLOWED_GROUPS = config['BOT']['allowed groups'].split(',')
GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
UNSET_BOSS_TEXT = f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{bot.name}.'
with open('hidden_items.txt') as f:
    HIDDEN_ITEMS_NAMES = f.read().split('\n')


def restricted(func):
    @functools.wraps(func)
    async def wrapper(chat, match):
        sender = chat.sender['username']
        for g in ALLOWED_GROUPS:
            if chat.is_group() and g in chat.message['chat']['title']:
                    return await func(chat, match, {'username': sender, 'group': g})
            elif await redis.sismember(g, sender):
                return await func(chat, match, {'username': sender, 'group': g})
        logger.info(f"{chat.sender.get('username')} tried to use the bot!")
        return await chat.reply('Questo è un bot per uso privato, mi spiace non sei autorizzato!')
    return wrapper


@bot.command(r'/setboss')
@restricted
async def setboss(chat, match, info):
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice'):
        return await chat.reply(f'Errore!\nSintassi corretta: /setboss@{bot.name} titano(o fenice) deadline')
    try:
        datetime.strptime(msg[2].replace('.', ':'), '%H:%M')
    except ValueError:
        return await chat.reply('Errore!\nOrario invalido!')
    group_members = await redis.smembers(info.get('group'))
    fields = {**{member: "" for member in group_members}, **{"boss": msg[1], "deadline": msg[2]}}
    await redis.delete(key)
    await redis.hmset_dict(key, fields)
    return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


@bot.command(r'^/listabotta')
@restricted
async def listabotta(chat, match, info):
    rv = await redis.hgetall(f"boss:{info.get('group')}")
    if rv:
        boss = rv.pop('boss').capitalize()
        deadline = rv.pop('deadline')
        formatted = f'{boss} {deadline}\n\n'
        negative = emoji.emojize(':x:', use_aliases=True)
        positive = emoji.emojize(':white_check_mark:', use_aliases=True)
        for username, status in rv.items():
            em = positive if status == 'ok' else status if status else negative
            if len(em) > 1:
                warning = emoji.emojize(':warning:', use_aliases=True)
                formatted += warning + f' *{username}*: {em}\n'
            else:
                line = f'{username}: {em}\n'
                if '/listabottatag' in chat.message['text']:
                    line = '@' + line if not status else line
                formatted += line
        return await chat.send_text(formatted, parse_mode='Markdown')
    else:
        chat.reply(UNSET_BOSS_TEXT)


@bot.command(r'^/botta')
@restricted
async def botta(chat, match, info):
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    success_text = f"{info.get('username')} ha dato la botta!"
    boss_list = await redis.hgetall(key)
    if boss_list:
        if len(msg) == 1:
            await redis.hset(key, info.get('username'), 'ok')
            return await chat.reply(success_text)
        elif len(msg) == 2:
            time = msg[1].replace('.', ':')
            try:
                datetime.strptime(time, '%H:%M')
                await redis.hset(key, info.get('username'), msg[1])
                return await chat.reply(f"{info.get('username')} darà la botta alle {time}!")
            except ValueError:
                admin_list_raw = await chat.get_chat_administrators()
                admin_list = [admin['user']['username'] for admin in admin_list_raw['result']]
                negative = emoji.emojize(':x:', use_aliases=True)
                if info.get('username') in admin_list and msg[1] in boss_list:
                    await redis.hset(key, msg[1], 'ok')
                    return await chat.reply(f'{msg[1]} ha dato la botta!')
                elif len(msg[1]) == 1:
                    if msg[1] == negative:
                        return await chat.reply('@Meck87 è un pirla!')
                    await redis.hset(key, info.get('username'), msg[1])
                    return await chat.reply(success_text)
                return await chat.reply('Errore!\nOrario invalido!')
        else:
            return await chat.reply(f'Errore!\nSintassi corretta: /botta@{bot.name} orario_botta(opzionale)')
    else:
        chat.reply(UNSET_BOSS_TEXT)


@bot.command(r'^/setalert')
@restricted
async def set_alert(chat, match, info):
    msg = chat.message['text'].split(' ')
    if len(msg) != 3:
        return await chat.reply('Errore!\nSintassi corretta: /setalert nomeoggetto prezzomassimo')
    item = await redis.hget('items', msg[1].capitalize())
    if item:
        item_id, value = item.split(',')
    else:
        return await chat.reply(f"Errore!\nNon ho trovato un oggetto chiamato: {msg[1]}")
    try:
        max_ = int(msg[2])
    except ValueError:
        return await chat.reply('Errore!\nIl prezzo massimo non è un numero')
    if max_ < int(value):
        return await chat.reply(f"Errore!\nIl prezzo massimo è minore del prezzo base dell'oggetto: {value}")

    new_alert = f'{item_id},{msg[2]},{msg[1]}'
    if await redis.hexists('alert', info.get('username')):
        other_alerts = await redis.hget('alert', info.get('username'))
        if msg[1] not in other_alerts:
            alerts = other_alerts + ':' + new_alert
            logger.debug(f'new alert added {alerts}')
        else:
            alerts = other_alerts.split(':')
            for i, alert in enumerate(alerts):
                if msg[1] in alert:
                    alerts[i] = new_alert
            alerts = ":".join(alerts)
            logger.debug(f'modified existing alert  {alerts}')
        await redis.hset('alert', info.get('username'), alerts)
    else:
        await redis.hset('alert', info.get('username'), new_alert)
    await chat.reply(f'Successo!Hai messo un alert su {msg[1]} al prezzo massimo di {msg[2]}')


@bot.command(r'^/showalerts')
@restricted
async def show_alerts(chat, match, info):
    alerts = await redis.hget('alert', info.get('username'))
    if not alerts:
        return await chat.reply('Non hai alerts settate --> /setalert')
    msg = 'Le tue alert sono:\n'
    for alert in alerts.split(':'):
        _, max_, name = alert.split(',')
        msg += f'{name}-->{max_}\n'
    await chat.reply(msg)


@bot.command(r'^/unsetalert')
@restricted
async def unset_alert(chat, match, info):
    msg = chat.message['text'].split(' ')
    if len(msg) != 2:
        return await chat.reply('Errore!\nSintassi corretta: /unsetalert nomeoggetto')
    alerts = await redis.hget('alert', info.get('username'))
    other_alerts = alerts.split(':')
    if not other_alerts:
        return await chat.reply('Non hai alerts settate --> /setalert')
    found = False
    for i, alert in enumerate(other_alerts):
        if msg[1] in alert:
            other_alerts.pop(i)
            found = True
    if found:
        await redis.hset('alert', info.get('username'), ':'.join(other_alerts))
        return await chat.reply(f'{msg[1]} rimosso dalle tue alerts!')
    await chat.reply(f'{msg[1]} non presente nelle tur alerts!')


@bot.command(r'^Attenzione! Appena messo piede nella stanza')
@restricted
async def namesolver(chat, match, info):
    msg = chat.message['text'].split('\n')[1].replace(' ', '')
    ris = await redis.hget('namesolver', msg)
    if not ris:
        return await chat.reply('non ho trovato nulla sorry')
    solutions = '\n'.join(ris.split(','))
    await chat.reply(f"Le possibili soluzioni sono:\n{solutions}")


def setup_coro(func):
    @functools.wraps(func)
    async def setup_coro_wrapper(*args, **kwargs):
        await asyncio.sleep(STARTUP_OFFSET)
        logger.info(f'{func.__name__} started!')
        try:
            if asyncio.iscoroutine(func):
                await func
            else:
                await func(*args, **kwargs)
        except asyncio.CancelledError:
            logger.info(f'{func.__name__} stopped!')
    return setup_coro_wrapper


def periodic(sleep_time):
    def periodic_coro(func):
        @functools.wraps(func)
        async def periodic_coro_wrapper(*args, **kwargs):
            while True:
                await func(*args, **kwargs)
                await asyncio.sleep(sleep_time)
        return periodic_coro_wrapper
    return periodic_coro


def clean_shutdown(signame, loop):
    logger.warning(f'{signame} recived, stopping!')
    for t in asyncio.Task.all_tasks():
        t.cancel()
    loop.create_task(stop_loop(loop))


async def stop_loop(loop):
    await asyncio.sleep(0.05)
    loop.stop()


async def db():
    global redis
    logger.info('creating redis connection')
    redis = await aioredis.create_redis(('localhost', 6379), encoding="utf-8")


@setup_coro
@periodic(30)
async def update_sales():
    async with bot.session.get('http://fenixweb.net:3300/api/v1/updatedshops/1') as s:
        sales = await s.json()
    for item in sales['res']:
        key = f"sale:{item.get('item_id')}:{item.get('code')}"
        value = f"{item.get('price')},{item.get('quantity')}"
        await redis.setex(key, 15*60, value)


@setup_coro
@periodic(15)
async def send_alert():
    async for key in redis.iscan(match='sale:*'):
        print('Matched:', key)


@setup_coro
@periodic(3600*12)
async def update_items_name():
    async with bot.session.get('http://fenixweb.net:3300/api/v1/items') as s:
        raw_items = await s.json()
    items = {item.get('name'): f"{item.get('id')},{item.get('value')}" for item in raw_items['res']}
    await redis.hmset_dict('items', items)
    ris = {}
    items_names = list(items.keys()) + HIDDEN_ITEMS_NAMES
    for name in items_names:
        incomplete_name = ''
        for i, char in enumerate(name):
            if i == 0 or i == len(name)-1:
                incomplete_name += char
            elif char == ' ':
                incomplete_name += '-'
            else:
                incomplete_name += '_'
        if incomplete_name not in ris:
            ris[incomplete_name] = name
        else:
            ris[incomplete_name] += ',' + name
    await redis.hmset_dict('namesolver', ris)


@setup_coro
@periodic(3600)
async def update_group_members():
    for group in ALLOWED_GROUPS:
        await redis.delete(group)
        async with bot.session.get(GROUP_URL+group) as s:
            group_members = await s.json()
        for member in group_members['res']:
            await redis.sadd(group, member['nickname'])


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(name)-12s %(levelname)-8s %(funcName)s:%(message)s',
        level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(clean_shutdown, signame, loop))
    logger.info(f"pid {os.getpid()}: send SIGINT or SIGTERM to exit.")

    background_coroutines = [
        db,
        setup_coro(bot.loop()),
        update_group_members,
        update_items_name,
        #  update_sales,
        #  send_alert
    ]

    for coro in background_coroutines:
        loop.create_task(coro())

    try:
        logger.info('starting event loop ')
        loop.run_forever()
    finally:
        loop.close()
