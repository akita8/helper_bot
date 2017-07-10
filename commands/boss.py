from datetime import datetime

import emoji

from utils import is_time, Config, ErrorReply


async def set_boss(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    group = info.get('group')
    key = f"boss:{group}"
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice', 'phoenix'):
        return await chat.reply(ErrorReply.INCORRECT_SYNTAX.format('/setboss titano (o fenice) deadline'))
    if not is_time(msg[2], '%d/%m/%Y-%H:%M'):
        return await chat.reply(ErrorReply.INVALID_TIME + ' formato corretto: giorno/mese/anno-ora:minuti')
    group_members = await redis.smembers(group)
    fields = {**{member: "" for member in group_members}, **{"boss": msg[1], "deadline": msg[2]}}
    await redis.delete(key)
    await redis.hmset_dict(key, fields)
    return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


async def lista_botta(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    rv = await redis.hgetall(f"boss:{info.get('group')}")
    if rv:
        if all(rv.values()) and not any([is_time(v) for k, v in rv.items() if k != 'deadline']):
            return chat.reply('KILL KILL KILL')
        boss = rv.pop('boss').capitalize()
        deadline = rv.pop('deadline')
        formatted = f'{boss} {deadline}\n\n'
        for username, status in rv.items():
            em = Config.CHECK if status == 'ok' else status if status else Config.CROSS
            if em.encode('utf-8') not in Config.EMOJI_BYTES:
                warning = emoji.emojize(':warning:', use_aliases=True)
                formatted += warning + f' *{username}*: {em}\n'
            else:
                line = f'{username}: {em}\n'
                if '/listabottatag' in chat.message['text']:
                    line = '@' + line if not status else line
                formatted += line if em != Config.CROSS else emoji.emojize(':exclamation:', use_aliases=True) + line
        return await chat.send_text(formatted, parse_mode='Markdown')
    else:
        chat.reply(f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.')


async def botta(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    sender = info.get('username')
    success_text = f"{sender} ha dato la botta!"
    boss_list = await redis.hgetall(key)
    reply_msg = ''
    if boss_list:
        if len(msg) == 1:
            boss_list[sender] = 'ok'
            reply_msg = success_text
        elif msg[1].encode('utf-8') in Config.EMOJI_BYTES:
            negative = emoji.emojize(':x:', use_aliases=True)
            if msg[1] == negative:
                return await chat.reply('@Meck87 è un pirla!')
            boss_list[sender] = msg[1]
            reply_msg = success_text
        elif len(msg) == 2:
            time = msg[1].replace('.', ':')
            try:
                datetime.strptime(time, '%H:%M')
                boss_list[sender] = msg[1]
                reply_msg = f"{sender} darà la botta alle {time}!"
            except ValueError:
                if chat.is_group() or chat.type == 'supergroup':
                    admin_list_raw = await chat.get_chat_administrators()
                    admin_list = [admin['user']['username'] for admin in admin_list_raw['result']]
                    if sender in admin_list and msg[1] in boss_list:
                        boss_list[msg[1]] = 'ok'
                        reply_msg = f'{msg[1]} ha dato la botta!'
                    else:
                        reply_msg = 'Errore!Non sei un amministratore o il giocatore non è nel gruppo!'
                else:
                    reply_msg = ErrorReply.INVALID_TIME
    else:
        reply_msg = f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.'
    await redis.hmset_dict(key, boss_list)
    await chat.reply(reply_msg)
    if all(boss_list.values()) and not any([is_time(v) for k, v in boss_list.items() if k != 'deadline']):
        await chat.send_text('KILL KILL KILL')


