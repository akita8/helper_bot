import asyncio

from utils import SolverData, ErrorReply


async def namesolver(chat, **kwargs):
    redis = kwargs.get('redis')
    msg = chat.message['text'].split('\n')[1].replace(' ', '')
    ris = await redis.hget('namesolver', msg)
    if not ris:
        return await chat.reply(ErrorReply.WORD_NOT_FOUND)
    solutions = ris.split(',')
    await chat.reply(f"Le possibili soluzioni sono:")
    for s in solutions:
        await chat.send_text(s)


async def wordsolver(chat, **_):
    target = chat.message['text'].split('\n')[1].replace(' ', '')[1:]
    loc = [i for i, letter in enumerate(target) if letter == '_']
    found_count = 0
    letters = {l for l in target.replace('_', '')}
    index = 0 if target[0] == '_' else SolverData.WORDS_ITA[len(target)][1][target[0]]
    await chat.reply('OK inizio a cercare!')
    for word in SolverData.WORDS_ITA[len(target)][0][index:]:
        attempt = ''
        for i, l in enumerate(word):
            if i in loc:
                if l in letters:
                    continue
                attempt += '_'
            else:
                attempt += l
        if attempt == target:
            found_count += 1
            await chat.send_text(word)
        if found_count == 3:
            return await chat.reply('Te ne ho mandate 3, cercarne di piu sarebbe uno spreco di tempo!')
        await asyncio.sleep(0.00001)
    else:
        await chat.reply(ErrorReply.WORD_NOT_FOUND)
