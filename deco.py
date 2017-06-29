import asyncio
import functools
import logging

from utils import Config


logger = logging.getLogger('decorators')


def restricted(redis):
    def restricted_deco(func):
        @functools.wraps(func)
        async def wrapper(chat, *args):
            match = args[0] if len(args) == 1 else args[1]
            sender = chat.sender['username']
            command = chat.message['text']
            base_info = {'username': sender}
            for g in Config.ALLOWED_GROUPS:
                info = {**base_info, 'group': g, 'args': command.split(' ')[1:]}
                if chat.is_group() and g in chat.message['chat']['title']:
                    logger.info(f"user->{sender} group->{g} command->{func.__name__}")
                    return await func(chat, match=match, info=info, redis=redis)
                elif await redis.sismember(g, sender):
                    logger.info(f"user->{sender} private command->{func.__name__}")
                    return await func(chat, match=match, info=info, redis=redis)
            else:
                if sender == Config.NAME:  # callbacks
                    logger.info(f"bot->{sender} callback command->{func.__name__}")
                    return await func(chat, match=match, info=base_info, redis=redis)
            logger.info(f"{chat.sender.get('username')} tried to use the bot!")
            return await chat.reply('Questo è un bot per uso privato, mi spiace non sei autorizzato!')
        return wrapper
    return restricted_deco


def must_be_forwarded_message(func):
    @functools.wraps(func)
    async def wrapper(chat, **kwargs):
        if not chat.message.get('forward_date'):
            return chat.reply("Errore!\nDeve essere un messaggio inoltrato!")
        return await func(chat, **kwargs)
    return wrapper


def strict_args_num(num, err):
    def strict_deco(func):
        @functools.wraps(func)
        async def wrapper(chat, match, info, redis):
            if len(info.get('args')) == num:
                return await func(chat, match, info, redis)
            return chat.reply(err)
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
