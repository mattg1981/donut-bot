import json
import urllib.request
from datetime import datetime, timedelta


USERS = {}


def get_user_weight(user: str) -> int:
    config = json.load(open('config.json'))

    # update user list weight (if needed)
    if "last_update" not in USERS or datetime.now() - timedelta(hours=8) >= USERS["last_update"]:
        USERS['users'] = json.load(urllib.request.urlopen(config["users_location"]))
        USERS['last_update'] = datetime.now()

    return next((u['weight'] for u in USERS['users'] if u['username'].lower() == user.lower()), 0)


