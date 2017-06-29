from datetime import datetime

import emoji

from utils import is_time, Config, ErrorReply


async def set_boss(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice', 'phoenix'):
        return await chat.reply(ErrorReply.INCORRECT_SYNTAX.format('/setboss titano(o fenice) deadline'))
    if not is_time(msg[2]):
        return await chat.reply(ErrorReply.INVALID_TIME)
    group_members = await redis.smembers(info.get('group'))
    fields = {**{member: "" for member in group_members}, **{"boss": msg[1], "deadline": msg[2]}}
    await redis.delete(key)
    await redis.hmset_dict(key, fields)
    return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


async def lista_botta(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    rv = await redis.hgetall(f"boss:{info.get('group')}")
    if rv:
        boss = rv.pop('boss').capitalize()
        deadline = rv.pop('deadline')
        formatted = f'{boss} {deadline}\n\n'
        negative = emoji.emojize(':x:', use_aliases=True)
        positive = emoji.emojize(':white_check_mark:', use_aliases=True)
        for username, status in rv.items():
            em = positive if status == 'ok' else status if status else negative
            if em.encode('utf-8') not in Config.EMOJI_BYTES:
                warning = emoji.emojize(':warning:', use_aliases=True)
                formatted += warning + f' *{username}*: {em}\n'
            else:
                line = f'{username}: {em}\n'
                if '/listabottatag' in chat.message['text']:
                    line = '@' + line if not status else line
                formatted += line
        return await chat.send_text(formatted, parse_mode='Markdown')
    else:
        chat.reply(f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.')


async def botta(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    success_text = f"{info.get('username')} ha dato la botta!"
    boss_list = await redis.hgetall(key)
    if boss_list:
        if len(msg) == 1:
            await redis.hset(key, info.get('username'), 'ok')
            return await chat.reply(success_text)
        elif msg[1].encode('utf-8') in Config.EMOJI_BYTES:
            negative = emoji.emojize(':x:', use_aliases=True)
            if msg[1] == negative:
                return await chat.reply('@Meck87 è un pirla!')
            await redis.hset(key, info.get('username'), msg[1])
            return await chat.reply(success_text)
        elif len(msg) == 2:
            time = msg[1].replace('.', ':')
            try:
                datetime.strptime(time, '%H:%M')
                await redis.hset(key, info.get('username'), msg[1])
                return await chat.reply(f"{info.get('username')} darà la botta alle {time}!")
            except ValueError:
                if chat.is_group():
                    admin_list_raw = await chat.get_chat_administrators()
                    admin_list = [admin['user']['username'] for admin in admin_list_raw['result']]
                    if info.get('username') in admin_list and msg[1] in boss_list:
                        await redis.hset(key, msg[1], 'ok')
                        return await chat.reply(f'{msg[1]} ha dato la botta!')
                    else:
                        return await chat.reply('Errore!Non sei un amministratore o il giocatore non è nel gruppo!')
                return await chat.reply(ErrorReply.INVALID_TIME)
        else:
            return await chat.reply(ErrorReply.INCORRECT_SYNTAX.format(f'/botta@{Config.NAME} orario_botta(opzionale)'))
    else:
        chat.reply(f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.')


