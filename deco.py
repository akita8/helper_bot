import asyncio
import functools
import logging

from utils import Config, ErrorReply


logger = logging.getLogger(__name__)


def restricted(redis):
    def restricted_deco(func):
        @functools.wraps(func)
        async def wrapper(chat, *args):
            match = args[0] if len(args) == 1 else args[1]
            cb_query = args[0] if len(args) == 2 else None
            sender = chat.sender['username']
            if sender == Config.NAME:
                return await func(chat, match=match, redis=redis, cb_query=cb_query)
            command = chat.message['text']
            base_info = {'username': sender}
            for g in Config.ALLOWED_GROUPS:
                logger.info(f"{chat.is_group()} {chat.message.get('chat').get('title')}")
                info = {**base_info, 'group': g, 'args': command.split(' ')[1:]}
                if chat.is_group() and g in chat.message['chat']['title']:
                    logger.info(f"user->{sender} group->{g} command->{func.__name__}")
                    return await func(chat, match=match, info=info, redis=redis, cb_query=cb_query)
                elif await redis.sismember(g, sender):
                    logger.info(f"user->{sender} private command->{func.__name__}")
                    return await func(chat, match=match, info=info, redis=redis, cb_query=cb_query)
            logger.info(f"{chat.sender.get('username')} tried to use the bot!")
            return await chat.reply('Questo è un bot per uso privato, mi spiace non sei autorizzato!')
        return wrapper
    return restricted_deco


def must_have_active_dungeon(func):
    @functools.wraps(func)
    async def wrapper(chat, **kwargs):
        redis = kwargs.get('redis')
        active_dungeon = await redis.hget(kwargs.get('info').get('username'), 'active_dungeon')
        if active_dungeon:
            return await func(chat, **{'active_dungeon': active_dungeon, **kwargs})
        return await chat.reply(ErrorReply.NO_ACTIVE_DUNGEONS)
    return wrapper


def must_be_forwarded_message(func):
    @functools.wraps(func)
    async def wrapper(chat, **kwargs):
        if not chat.message.get('forward_date'):
            return chat.reply("Errore!\nDeve essere un messaggio inoltrato!")
        return await func(chat, **kwargs)
    return wrapper


def strict_args_num(expression):
    def strict_deco(func):
        @functools.wraps(func)
        async def wrapper(chat, **kwargs):
            if eval(expression.format(len(kwargs.get('info').get('args')))):
                return await func(chat, **kwargs)
            return chat.reply(f"Errore!\nTroppi argomenti per il comando.")
        return wrapper
    return strict_deco


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
