import asyncio
import functools
import logging

from utils import Config


logger = logging.getLogger('decorators')


def restricted(redis):
    def restricted_deco(func):
        @functools.wraps(func)
        async def wrapper(chat, match):
            sender = chat.sender['username']
            for g in Config.ALLOWED_GROUPS:
                if chat.is_group() and g in chat.message['chat']['title']:
                        return await func(chat, match, {'username': sender, 'group': g}, redis)
                elif await redis.sismember(g, sender):
                    return await func(chat, match, {'username': sender, 'group': g}, redis)
            logger.info(f"{chat.sender.get('username')} tried to use the bot!")
            return await chat.reply('Questo è un bot per uso privato, mi spiace non sei autorizzato!')
        return wrapper
    return restricted_deco


def setup_coro(func):
    @functools.wraps(func)
    async def setup_coro_wrapper(*args, **kwargs):
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
