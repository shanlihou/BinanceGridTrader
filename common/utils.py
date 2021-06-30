from . import const
import json

def get_binance_user_json():
    with open(const.BIN_USER_JSON) as fr:
        return json.load(fr)