import configparser
import os

from logging import getLogger

import emoji

from .utils import markup_inline_keyboard

logger = getLogger(__name__)


def load_user_config():
    config = configparser.ConfigParser()
    try:
        config.read('config.ini') or config.read(os.environ['CONFIG_FILE'])
    except KeyError:
        logger.error('config file NOT FOUND')
        return None, None, None
    return config['BOT']['allowed groups'].split(','), config['BOT']['name'], config['BOT']['token']


class BotConfig:

    ALLOWED_GROUPS, NAME, TOKEN = load_user_config()

    @classmethod
    def check(cls):
        return all((cls.ALLOWED_GROUPS, cls.NAME, cls.TOKEN))


class ErrorReply:
    INCORRECT_SYNTAX = 'Errore!\nSintassi corretta: {}'
    INVALID_TIME = 'Errore!\nOrario invalido!'
    WORD_NOT_FOUND = "Non ho trovato nulla:( per favore avvisa un admin così possiamo migliorare il servizio!"
    NO_ACTIVE_DUNGEONS = 'Errore!\nNon hai un dungeon attivo, mandami il messaggio di entrata nel dungeon:)'


class Url:
    ITEMS = 'http://fenixweb.net:3300/api/v1/items'
    GROUP = 'http://fenixweb.net:3300/api/v2/oI65t30vbkwBisPw6668/team/'
    SHOPS = 'http://fenixweb.net:3300/api/v1/updatedshops/1'


class Emoji:
    BYTES = [e.replace(' ', '').encode('utf-8') for e in emoji.UNICODE_EMOJI]

    ARROW_UP = emoji.emojize(':arrow_up:', use_aliases=True)
    ARROW_LEFT = emoji.emojize(':arrow_left:', use_aliases=True)
    ARROW_RIGHT = emoji.emojize(':arrow_right:', use_aliases=True)
    NEUTRAL = emoji.emojize(':full_moon_with_face:', use_aliases=True)
    POSITIVE = emoji.emojize(':green_heart:', use_aliases=True)
    NEGATIVE = emoji.emojize(':red_circle:', use_aliases=True)
    CROSS = emoji.emojize(':x:', use_aliases=True)
    CHECK = emoji.emojize(':white_check_mark:', use_aliases=True)
    VACATION = emoji.emojize(':calendar:', use_aliases=True)


class Dungeon:
    RE = {
        "(^L'aria si fa più pesante.|^Incontri un)": 'mostro',
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
        "In questa stanza non noti nessuna porta, al loro posto 3 incisioni con un pulsante ciascuna": 'incisioni',
    }
    EMOJIS = {
        'mostro': emoji.emojize(':boar:', use_aliases=True),
        'tributo': Emoji.NEGATIVE,
        'vecchia': Emoji.NEUTRAL,
        'due porte': Emoji.NEUTRAL,
        'aiuta': Emoji.POSITIVE,
        'ascia': emoji.emojize(':dragon_face:', use_aliases=True),
        'desideri': Emoji.NEUTRAL,
        'fontana': Emoji.POSITIVE,
        'leve': Emoji.NEUTRAL,
        'marinaio': Emoji.NEUTRAL,
        'mattonella': emoji.emojize(':dragon_face:', use_aliases=True),
        'meditazione': Emoji.NEUTRAL,
        "mercante": Emoji.NEUTRAL,
        "pozzo": Emoji.NEGATIVE,
        "pulsantiera": Emoji.NEGATIVE,
        "monete": emoji.emojize(':moneybag:', use_aliases=True),
        'raro': Emoji.POSITIVE,
        'scrigno': Emoji.POSITIVE,
        'stanza vuota': Emoji.POSITIVE,
        'spada': emoji.emojize(':dollar:', use_aliases=True),
        'predone': Emoji.NEUTRAL,
        'trappola': Emoji.NEGATIVE,
        'incisioni': Emoji.NEGATIVE,
        '': emoji.emojize(':question:', use_aliases=True)
    }
    ROOMS = set(RE.values())
    LENGTH = {
        "Il Burrone Oscuro": 10,
        "La Grotta Infestata": 15,
        "Il Vulcano Impetuoso": 20,
        "La Caverna degli Orchi": 25,
        "Il Cratere Ventoso": 30,
        "Il Deserto Rosso": 40,
        "La Foresta Maledetta": 45,
        "La Vetta delle Anime": 50,
        "Il Lago Evanescente": 55,
        "Il Labirinto Spettrale": 60,
    }
    ACRONYMS = {''.join([w[0].lower() for w in key.split(' ')][1:]): key for key in LENGTH}
    DIRECTIONS = {Emoji.ARROW_LEFT: 0, Emoji.ARROW_UP: 1, Emoji.ARROW_RIGHT: 2}
    MARKUP = markup_inline_keyboard([[(key, f"stats1click-{key}")] for key in LENGTH])

    @staticmethod
    def length(name):
        dungeon_name = ' '.join(name.split(' ')[:-1])
        return Dungeon.LENGTH[dungeon_name]

    @staticmethod
    def stringify_room(i, left, up, right, emojis):
        def room_emoji(room):
            return emojis.get(room) if 'mostro' not in room else emojis.get('mostro')
        return f"---*Stanza*: *{i}*---\n{Emoji.ARROW_LEFT} {left} {room_emoji(left)}\n" \
               f"{Emoji.ARROW_UP} {up} {room_emoji(up)}\n" \
               f"{Emoji.ARROW_RIGHT} {right} {room_emoji(right)}\n"

    @staticmethod
    def map_directions(dungeon, start, end, user, json=True):
        return markup_inline_keyboard(
            [[(emoji.emojize(":arrow_double_up:", use_aliases=True), f"mapclick-{dungeon}:{start}:{end}:up:{user}")],
             [(emoji.emojize(
                 ":arrow_double_down:", use_aliases=True), f"mapclick-{dungeon}:{start}:{end}:down:{user}")]],
            json=json)
