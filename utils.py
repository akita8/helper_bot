import os
import configparser
import collections

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


class Config:

    ALLOWED_GROUPS, NAME, TOKEN = load_user_config()

    ITEMS_URL = 'http://fenixweb.net:3300/api/v1/items'
    GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
    SHOPS_URL = 'http://fenixweb.net:3300/api/v1/updatedshops/1'

    EMOJI_BYTES = [e.replace(' ', '').encode('utf-8') for e in emoji.UNICODE_EMOJI]


class SolverData:

    WORDS_ITA, HIDDEN_ITEMS_NAMES = load_solvers_words()



