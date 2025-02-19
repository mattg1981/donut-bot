import json
import urllib.request
from datetime import datetime, timedelta

from database import database

CACHE = {
    'users': {},
    'special_members': {},
    'moderators': {},
}


def get_user_weight(user: str) -> int:
    """
    Returns the governance weight of a user.
    :param user: The user
    :return:  The users governance weight
    """
    config = json.load(open('config.json'))
    u = CACHE['users']

    # update user list weight (if needed)
    if "last_update" not in u or datetime.now() - timedelta(minutes=30) >= u["last_update"]:
        u['users'] = json.load(urllib.request.urlopen(config["users_location"]))
        u['last_update'] = datetime.now()

    return next((u['weight'] for u in u['users'] if u['username'].lower() == user.lower()), 0)

def is_special_member(user: str, community: str) -> bool:
    """
    Check if a user is a special member in a given community.
    :param user: The user
    :param community: The community
    :return: True if the user is a special member, False otherwise
    """
    config = json.load(open('config.json'))
    sm = CACHE['special_members']

    # update user list weight (if needed)
    if "last_update" not in sm or datetime.now() - timedelta(minutes=10) >= sm["last_update"]:
        sm['members'] = json.load(urllib.request.urlopen(config["membership"]['members']))
        sm['last_update'] = datetime.now()

    member = next((smember for smember in sm['members'] if smember['redditor'].lower() == user.lower() and (smember['community'] == community.lower() or smember['community'] == 'all')), None)
    return member is not None


def is_moderator(user: str, community: str) -> bool:
    mod_cache = CACHE['moderators']

    # update user list weight (if needed)
    if "last_update" not in mod_cache or datetime.now() - timedelta(minutes=10) >= mod_cache["last_update"]:
        dist_round = database.get_distribution_round()
        result = json.load(urllib.request.urlopen(
            f'https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/moderators/moderators_{dist_round}.json'))

        mod_cache['mods'] = result
        mod_cache['last_update'] = datetime.now()

    return next((m for m in mod_cache['mods'] if m["name"] == user and m['community'] == community), None) is not None
