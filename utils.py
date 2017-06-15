import os
import configparser
import collections


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

    indexed_data = collections.defaultdict(list)
    for word in data:
        indexed_data[len(word)].append(word)
    print('FATTO!')
    return indexed_data, hidden


class Config:

    ALLOWED_GROUPS, NAME, TOKEN = load_user_config()

    ITEMS_URL = 'http://fenixweb.net:3300/api/v1/items'
    GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
    SHOPS_URL = 'http://fenixweb.net:3300/api/v1/updatedshops/1'


class SolverData:

    WORDS_ITA, HIDDEN_ITEMS_NAMES = load_solvers_words()



