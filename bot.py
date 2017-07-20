import asyncio
import functools
import logging
import os
import signal

import aioredis
import aiotg

from helper_bot.background import update_group_members, update_items_name, build_maps
from helper_bot.button_callbacks import gabbia_buttons_reply, gabbia_choice, stats_button_reply_phase1, \
    stats_choice_phase1, stats_choice_phase2, map_next, dungeon_exchange, confirm_trade
from helper_bot.commands.dungeon import set_dungeon, log_user_action, log_user_position, log_user_direction, \
    close_dungeon, get_map, next_room, get_current_dungeon, trade_dungeon, expire_dungeon, map_todo
from helper_bot.commands.riddle_solvers import wordsolver
from helper_bot.commands.boss import set_boss, botta, lista_botta
from helper_bot.decorators import restricted, setup_coro
from helper_bot.settings import BotConfig, Emoji, Dungeon, SolverData

logging.basicConfig(
    format='%(asctime)s %(name)-12s %(levelname)-8s %(funcName)s:%(message)s',
    level=logging.INFO)
logger = logging.getLogger('bot')


async def stop_loop(loop, redis):
    await asyncio.sleep(0.05)
    redis.close()
    await redis.wait_closed()
    loop.stop()


def clean_shutdown(loop, signame, redis):
    logger.warning(f'{signame} received, stopping!')
    for t in asyncio.Task.all_tasks():
        t.cancel()
    loop.create_task(stop_loop(loop, redis))


def add_signal_handlers(loop, redis):
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(clean_shutdown, loop, signame, redis))
    logger.info(f"pid {os.getpid()}: send SIGINT or SIGTERM to exit.")


def create_bot(redis):
    bot = aiotg.Bot(BotConfig.TOKEN, name=BotConfig.NAME)

    restricted_deco = restricted(redis)
    commands = [
        (set_boss, r'^/setboss'),
        (botta, r'^/botta'),
        (lista_botta, r'^/listabotta'),
        (gabbia_buttons_reply, r'^Attenzione! Appena messo piede nella stanza'),
        (stats_button_reply_phase1, '^/stats'),
        (set_dungeon, r'^Sei stato aggiunto alla Lista Avventurieri del dungeon (.*)!'),
        (close_dungeon, r'^/quitdg'),
        (get_map, r'^/mappa'),
        (log_user_position, r'Stanza (\d+)/(\d+)'),
        (log_user_direction, rf"({Emoji.ARROW_UP}|{Emoji.ARROW_LEFT}|{Emoji.ARROW_RIGHT})"),
        (next_room, r'^/next'),
        (get_current_dungeon, r'^/dungeon'),
        (trade_dungeon, r'^/scambio'),
        (expire_dungeon, r'^/cancelladg'),
        (map_todo, r'^/todo'),
        # (set_expire_date, r'')
        # (set_alert, r'^/setalert'),
        # (unset_alert, r'^/unsetalert'),
        # (show_alerts, r'^/showalerts'),
    ]

    if SolverData.check():
        commands += [(wordsolver, r'^Sul portone del rifugio')]

    dungeon_commands = [(log_user_action, '^'+string) for string in Dungeon.RE]
    commands += dungeon_commands

    callbacks = [
        (gabbia_choice, 'gabbiaclick-(\w+|\d+)'),
        (stats_choice_phase1, 'stats1click-(.+)'),
        (stats_choice_phase2, 'stats2click-(.+)'),
        (map_next, 'mapclick-(.+)'),
        (dungeon_exchange, 'tradedgclick-(.+)'),
        (confirm_trade, 'confirmtradeclick-(.+)')
    ]

    for fn, re in commands:
        bot.add_command(re, restricted_deco(fn))
    for fn, re in callbacks:
        bot.add_callback(re, restricted_deco(fn))

    return bot


def create_tasks(loop, redis):
    bot = create_bot(redis)

    coroutines = [
        setup_coro(bot.loop())(),
        update_group_members(bot, redis),
        update_items_name(bot, redis),
        build_maps(bot, redis)]

    for coro in coroutines:
        loop.create_task(coro)


def run_bot():
    if BotConfig.check():
        loop = asyncio.get_event_loop()

        logger.info('creating redis connection')
        redis_conn = loop.run_until_complete(aioredis.create_redis(('localhost', 6379), encoding="utf-8"))

        logger.info('adding signal handlers')
        add_signal_handlers(loop, redis_conn)

        logger.info('creating tasks: bot and background coros')
        create_tasks(loop, redis_conn)

        try:
            logger.info('starting event loop ')
            loop.run_forever()
        finally:
            loop.close()


if __name__ == '__main__':
    run_bot()
