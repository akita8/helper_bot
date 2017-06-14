import os
import configparser


config = configparser.ConfigParser()

try:
    config.read('config.ini') or config.read(os.environ['CONFIG_FILE'])
except KeyError:
    print('config file NOT FOUND')
    exit()


class Config:

    ALLOWED_GROUPS = config['BOT']['allowed groups'].split(',')
    NAME = config['BOT']['name']
    TOKEN = config['BOT']['token']

    ITEMS_URL = 'http://fenixweb.net:3300/api/v1/items'
    GROUP_URL = 'http://fenixweb.net:3300/api/v1/team/'
    SHOPS_URL = 'http://fenixweb.net:3300/api/v1/updatedshops/1'

    with open('hidden_items.txt') as f:
        HIDDEN_ITEMS_NAMES = f.read().split('\n')
