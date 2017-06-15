import asyncio
import functools
import logging
import os
import signal

import aioredis
import aiotg

from utils import Config
from commands import \
    set_boss, botta, lista_botta, namesolver, set_alert, unset_alert, show_alerts, wordsolver
from deco import restricted, setup_coro
from background import update_group_members, update_items_name


logging.basicConfig(
    format='%(asctime)s %(name)-12s %(levelname)-8s %(funcName)s:%(message)s',
    level=logging.INFO)
logger = logging.getLogger('core')


async def stop_loop(loop, redis):
    await asyncio.sleep(0.05)
    redis.close()
    await redis.wait_closed()
    loop.stop()


def clean_shutdown(signame, redis):
    logger.warning(f'{signame} recived, stopping!')
    for t in asyncio.Task.all_tasks():
        t.cancel()
    loop.create_task(stop_loop(loop, redis))


def add_signal_handlers(redis):
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(clean_shutdown, signame, redis))
    logger.info(f"pid {os.getpid()}: send SIGINT or SIGTERM to exit.")


def create_bot(redis):
    bot = aiotg.Bot(Config.TOKEN, name=Config.NAME)
    restricted_deco = restricted(redis)
    commands = [
        (set_boss, r'^/setboss'),
        (botta, r'^/botta'),
        (lista_botta, r'^/listabotta'),
        (namesolver, r'^Attenzione! Appena messo piede nella stanza'),
        (wordsolver, r'^Sul portone del rifugio vi è una piccola pulsantiera'),
        (set_alert, r'^/setalert'),
        (unset_alert, r'^/unsetalert'),
        (show_alerts, r'^/showalerts')]
    for fn, re in commands:
        bot.add_command(re, restricted_deco(fn))
    return bot


def create_tasks(redis):
    bot = create_bot(redis)

    coroutines = [
        setup_coro(bot.loop())(),
        update_group_members(bot, redis),
        update_items_name(bot, redis)]

    for coro in coroutines:
        loop.create_task(coro)


loop = asyncio.get_event_loop()

logger.info('creating redis connection')
redis_conn = loop.run_until_complete(aioredis.create_redis(('localhost', 6379), encoding="utf-8"))

logger.info('adding signal handlers')
add_signal_handlers(redis_conn)

logger.info('creating tasks: bot and background coros')
create_tasks(redis_conn)

try:
    logger.info('starting event loop ')
    loop.run_forever()
finally:
    loop.close()
