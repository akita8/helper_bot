from helper_bot.settings import ErrorReply


async def set_alert(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    msg = chat.message['text'].split(' ')
    if len(msg) != 3:
        return await chat.reply(ErrorReply.INCORRECT_SYNTAX.format('/setalert nomeoggetto prezzomassimo'))
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


async def show_alerts(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    alerts = await redis.hget('alert', info.get('username'))
    if not alerts:
        return await chat.reply('Non hai alerts settate --> /setalert')
    msg = 'Le tue alert sono:\n'
    for alert in alerts.split(':'):
        _, max_, name = alert.split(',')
        msg += f'{name}-->{max_}\n'
    await chat.reply(msg)


async def unset_alert(chat, **kwargs):
    redis = kwargs.get('redis')
    info = kwargs.get('info')
    msg = chat.message['text'].split(' ')
    if len(msg) != 2:
        return await chat.reply(ErrorReply.INCORRECT_SYNTAX.format('/unsetalert nomeoggetto'))
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