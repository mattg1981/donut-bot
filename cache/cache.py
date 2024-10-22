import json
import urllib.request
from datetime import datetime, timedelta


CACHE = {
    'users': {},
    'special_members': {}
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
