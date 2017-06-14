import emoji
from datetime import datetime

from config import Config


async def set_boss(chat, match, info, redis):
    key = f"boss:{info.get('group')}"
    msg = chat.message['text'].split(' ')
    if len(msg) != 3 or msg[1].lower() not in ('titano', 'fenice'):
        return await chat.reply(f'Errore!\nSintassi corretta: /setboss@{Config.NAME} titano(o fenice) deadline')
    try:
        datetime.strptime(msg[2].replace('.', ':'), '%H:%M')
    except ValueError:
        return await chat.reply('Errore!\nOrario invalido!')
    group_members = await redis.smembers(info.get('group'))
    fields = {**{member: "" for member in group_members}, **{"boss": msg[1], "deadline": msg[2]}}
    await redis.delete(key)
    await redis.hmset_dict(key, fields)
    return await chat.reply(f'Successo!\nHai impostato una nuova scalata!\nBoss: {msg[1]}\nDeadline: {msg[2]}')


async def lista_botta(chat, match, info, redis):
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
        chat.reply(f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.')


async def botta(chat, match, info, redis):
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
            return await chat.reply(f'Errore!\nSintassi corretta: /botta@{Config.NAME} orario_botta(opzionale)')
    else:
        chat.reply(f'Errore!\nNon ho trovato boss impostati --> /setboss o /setboss@{Config.NAME}.')


async def set_alert(chat, match, info, redis):
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

        else:
            alerts = other_alerts.split(':')
            for i, alert in enumerate(alerts):
                if msg[1] in alert:
                    alerts[i] = new_alert
            alerts = ":".join(alerts)
        await redis.hset('alert', info.get('username'), alerts)
    else:
        await redis.hset('alert', info.get('username'), new_alert)
    await chat.reply(f'Successo!Hai messo un alert su {msg[1]} al prezzo massimo di {msg[2]}')


async def show_alerts(chat, match, info, redis):
    alerts = await redis.hget('alert', info.get('username'))
    if not alerts:
        return await chat.reply('Non hai alerts settate --> /setalert')
    msg = 'Le tue alert sono:\n'
    for alert in alerts.split(':'):
        _, max_, name = alert.split(',')
        msg += f'{name}-->{max_}\n'
    await chat.reply(msg)


async def unset_alert(chat, match, info, redis):
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


async def namesolver(chat, match, info, redis):
    msg = chat.message['text'].split('\n')[1].replace(' ', '')
    ris = await redis.hget('namesolver', msg)
    if not ris:
        return await chat.reply('non ho trovato nulla sorry')
    solutions = '\n'.join(ris.split(','))
    await chat.reply(f"Le possibili soluzioni sono:\n{solutions}")
