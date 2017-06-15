from utils import Config, SolverData
from deco import periodic, setup_coro


@setup_coro
@periodic(30)
async def update_sales(bot, redis):
    async with bot.session.get(Config.SHOPS_URL) as s:
        sales = await s.json()
    for item in sales['res']:
        key = f"sale:{item.get('item_id')}:{item.get('code')}"
        value = f"{item.get('price')},{item.get('quantity')}"
        await redis.setex(key, 15*60, value)


@setup_coro
@periodic(15)
async def send_alert(redis):
    async for key in redis.iscan(match='sale:*'):
        print('Matched:', key)


@setup_coro
@periodic(3600*12)
async def update_items_name(bot, redis):
    async with bot.session.get(Config.ITEMS_URL) as s:
        raw_items = await s.json()
    items = {item.get('name'): f"{item.get('id')},{item.get('value')}" for item in raw_items['res']}
    await redis.hmset_dict('items', items)
    ris = {}
    items_names = list(items.keys()) + SolverData.HIDDEN_ITEMS_NAMES
    for name in items_names:
        incomplete_name = ''
        for i, char in enumerate(name):
            if i == 0 or i == len(name)-1:
                incomplete_name += char
            elif char == ' ':
                incomplete_name += '-'
            else:
                incomplete_name += '_'
        if incomplete_name not in ris:
            ris[incomplete_name] = name
        else:
            ris[incomplete_name] += ',' + name
    await redis.hmset_dict('namesolver', ris)


@setup_coro
@periodic(3600)
async def update_group_members(bot, redis):
    for group in Config.ALLOWED_GROUPS:
        await redis.delete(group)
        async with bot.session.get(Config.GROUP_URL+group) as s:
            group_members = await s.json()
        for member in group_members['res']:
            await redis.sadd(group, member['nickname'])
