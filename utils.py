import os
import configparser
import datetime
import json

import emoji


def load_user_config():
    config = configparser.ConfigParser()
    try:
        config.read('config.ini') or config.read(os.environ['CONFIG_FILE'])
    except KeyError:
        print('config file NOT FOUND')
        exit()
    return config['BOT']['allowed groups'].split(','), config['BOT']['name'], config['BOT']['token']


def load_solvers_words():
    with open('hidden_items.txt') as f:
        hidden = f.read().split('\n')
    with open('ITA5-12.txt', encoding='ISO-8859-1') as f:
        data = f.read().split('\n')
        data.pop(-1)

    indexed_data = {}
    for word in data:
        l = len(word)
        first_letter = word[0]
        if l not in indexed_data:
            indexed_data[l] = ([word], {})
        else:
            indexed_data[l][0].append(word)
        if first_letter not in indexed_data[l][1]:
            indexed_data[l][1][first_letter] = len(indexed_data[l][0]) - 1
    return indexed_data, hidden


def is_time(time_string):
    try:
        datetime.datetime.strptime(time_string.replace('.', ':'), '%H:%M')
    except ValueError:
        return False
    return True


def is_number(number):
    try:
        int(number)
    except ValueError:
        return False
    return True


def dungeon_len(name):
    dungeon_name = ' '.join(name.split(' ')[:-1])
    return Config.DUNGEONS_LENGTH[dungeon_name]


def markup_inline_keyboard(buttons):
    markup = {
        'type': 'InlineKeyboardMarkup',
        'inline_keyboard': []}
    for button_level in buttons:
        formatted_level = []
        for button in button_level:
            text, cb_data = button
            formatted_level.append({'type': 'InlineKeyboardButton', 'text': text, 'callback_data': cb_data})
        markup['inline_keyboard'].append(formatted_level)
    return json.dumps(markup)


def stringify_dungeon_room(i, left, up, right):
    return f"*Stanza*: {i}\n{Config.ARROW_LEFT} --> {left} {Config.DUNGEONS_EMOJIS.get(left)}\n" \
           f"{Config.ARROW_UP} --> {up} {Config.DUNGEONS_EMOJIS.get(up)}\n" \
           f"{Config.ARROW_RIGHT} --> {right} {Config.DUNGEONS_EMOJIS.get(right)}\n"


class Config:

    ALLOWED_GROUPS, NAME, TOKEN = load_user_config()

    ITEMS_URL = 'http://fenixweb.net:3300/api/v1/items'
    GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
    SHOPS_URL = 'http://fenixweb.net:3300/api/v1/updatedshops/1'

    EMOJI_BYTES = [e.replace(' ', '').encode('utf-8') for e in emoji.UNICODE_EMOJI]

    ARROW_UP = emoji.emojize(':arrow_up:', use_aliases=True)
    ARROW_LEFT = emoji.emojize(':arrow_left:', use_aliases=True)
    ARROW_RIGHT = emoji.emojize(':arrow_right:', use_aliases=True)
    NEUTRAL = emoji.emojize(':full_moon_with_face:', use_aliases=True)
    POSITIVE = emoji.emojize(':green_heart:', use_aliases=True)
    NEGATIVE = emoji.emojize(':red_circle:', use_aliases=True)
    DUNGEONS_RE = {
        'Incontri un': 'mostro',
        'Aprendo la porta ti ritrovi in un ambiente aperto,': 'vecchia',
        'Oltrepassando la porta ti trovi davanti ad altre due porte': 'due porte',
        "Appena entrato nella stanza vedi nell'angolo": 'aiuta',
        "Questa stanza è vuota, c'è solo una piccola fessura sul muro di fronte": 'tributo',
        "Un cartello con un punto esclamativo ti preoccupa, al centro della stanza": 'ascia',
        "Davanti a te si erge un portale completamente rosso": 'desideri',
        "Appena entrato nella stanza noti subito una strana fontana situata nel centro": 'fontana',
        "Al centro della stanza ci sono 3 leve": 'leve',
        "Nella stanza incontri un marinaio con aria furba": 'marinaio',
        "Entri nella stanza e per sbaglio pesti una mattonella leggermente rovinata": 'mattonella',
        "Raggiungi una stanza con un'incisione profonda:": 'meditazione',
        "Nella stanza incontri un viandante": "mercante",
        "Una luce esagerata ti avvolge, esci in un piccolo spiazzo": "pozzo",
        "Appena aperta la porta della stanza": "pulsantiera",
        "Al centro della stanza vedi un mucchietto di monete": "monete",
        "Raggiungi una stanza suddivisa in due, vedi un oggetto per lato": 'raro',
        "Nella stanza sembra esserci uno scrigno pronto per essere aperto": 'scrigno',
        "Entri in una stanza apparentemente vuota": 'stanza vuota',
        "Entri in una stanza piena d'oro luccicante e una spada": 'spada',
        "Nella stanza incontri un predone del deserto dall'aria docile": 'predone',
        "Camminando per raggiungere la prossima stanza, una trappola": 'trappola',
        "Percorrendo un corridoio scivoli su una pozzanghera": 'trappola',
        "Vedi un Nano della terra di Grumpi e ti chiedi": 'trappola',
        "Uno strano pulsante rosso come un pomodoro ti incuriosisce": 'trappola',
    }
    DUNGEONS_EMOJIS = {
        'mostro': emoji.emojize(':boar:', use_aliases=True),
        'tributo': NEGATIVE,
        'vecchia': NEUTRAL,
        'due porte': NEUTRAL,
        'aiuta': POSITIVE,
        'ascia': NEUTRAL,
        'desideri': NEUTRAL,
        'fontana': POSITIVE,
        'leve': NEUTRAL,
        'marinaio': NEUTRAL,
        'mattonella': POSITIVE,
        'meditazione': NEUTRAL,
        "mercante": NEUTRAL,
        "pozzo": NEGATIVE,
        "pulsantiera": NEGATIVE,
        "monete": POSITIVE,
        'raro': POSITIVE,
        'scrigno': POSITIVE,
        'stanza vuota': POSITIVE,
        'spada': emoji.emojize(':heavy_dollar_sign:', use_aliases=True),
        'predone': NEUTRAL,
        'trappola': NEGATIVE,
        '': emoji.emojize(':question:', use_aliases=True)
    }
    DUNGEONS_ROOMS = set(DUNGEONS_RE.values()).union({'gabbia'})
    DUNGEONS_LENGTH = {
        "Il Burrone Oscuro": 10,
        "La Grotta Infestata": 15,
        "Il Vulcano Impetuoso": 20,
        "La Caverna degli Orchi": 25,
        "Il Cratere Ventoso": 30,
        "Il Deserto Rosso": 40,
        "La Foresta Maledetta": 45,
        "La Vetta delle Anime": 50,
        "Il Lago Evanescente": 55,
    }
    DUNGEONS_DIRECTIONS = {ARROW_LEFT: 0, ARROW_UP: 1, ARROW_RIGHT: 2}
    DUNGEON_MARKUP = markup_inline_keyboard([[(key, f"stats1click-{key}")] for key in DUNGEONS_LENGTH])


class SolverData:

    WORDS_ITA, HIDDEN_ITEMS_NAMES = load_solvers_words()


class ErrorReply:
    INCORRECT_SYNTAX = 'Errore!\nSintassi corretta:{}'
    INVALID_TIME = 'Errore!\nOrario invalido!'
    WORD_NOT_FOUND = "Non ho trovato nulla:( per favore avvisa un admin così possiamo migliorare il servizio!"
    NO_ACTIVE_DUNGEONS = 'Errore!\nNon hai un dungeon attivo, mandami il messaggio di entrata nel dungeon:)'
