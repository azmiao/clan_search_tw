import json
import os


# 首次启动本插件的时候创建配置文件
current_dir = os.path.join(os.path.dirname(__file__), 'config.json')
if not os.path.exists(current_dir):
    with open(current_dir, 'w', encoding='UTF-8') as sf:
        # noinspection PyTypeChecker
        json.dump({}, sf, indent=4, ensure_ascii=False)


# 绑定公会
async def lock_clan(server: str, clan_name: str, group_id: str) -> str:
    with open(current_dir, 'r', encoding='UTF-8') as af:
        f_data = json.load(af)
    f_data[group_id] = {}
    f_data[group_id]['server'] = server
    f_data[group_id]['clan_name'] = clan_name
    with open(current_dir, 'w', encoding='UTF-8') as f:
        # noinspection PyTypeChecker
        json.dump(f_data, f, indent=4, ensure_ascii=False)
    msg = f'QQ群：{group_id} 已成功绑定{server}服公会“{clan_name}”'
    return msg


# 多个绑定选择触发
async def select_all_clan(clan_score: dict) -> str:
    num = clan_score['total']
    msg = '查询到该名字为前缀的公会如下:'
    for num_id in range(num):
        data_id = list(clan_score['data'].keys())[num_id]
        clan_name = clan_score['data'][data_id]['clan_name']
        msg = msg + '\n' + str(num_id + 1) + '. ' + str(clan_name)
    return msg


# 解绑公会
async def unlock_clan(group_id: str) -> str:
    with open(current_dir, 'r', encoding='UTF-8') as af:
        f_data = json.load(af)
    clan_name = f_data[group_id]['clan_name']
    f_data.pop(group_id)
    with open(current_dir, 'w', encoding='UTF-8') as f:
        # noinspection PyTypeChecker
        json.dump(f_data, f, indent=4, ensure_ascii=False)
    msg = f'QQ群：{group_id} 已成功解绑公会"{clan_name}"'
    return msg


# 查询公会绑定
async def judge_lock(group_id: str) -> (str, bool):
    with open(current_dir, 'r', encoding='UTF-8') as af:
        f_data = json.load(af)
    if group_id in list(f_data.keys()):
        server = f_data[group_id]['server']
        clan_name = f_data[group_id]['clan_name']
        msg = f'本群：{group_id} 已成功绑定{server}服公会“{clan_name}”'
        return msg, True
    else:
        msg = f'本群：{group_id} 暂未绑定任何公会'
        return msg, False
