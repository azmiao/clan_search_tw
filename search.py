import json
import os
import re
import shutil

from httpx import AsyncClient

from yuiChyan.util.chart_generator import create_table, save_fig_as_image

# 图片路径 | 启动时删除重建
image_dir = os.path.join(os.path.dirname(__file__), 'images')
if os.path.exists(image_dir):
    shutil.rmtree(image_dir)
os.makedirs(image_dir, exist_ok=True)


# 设置当前源
async def set_source(source_name: str) -> bool:
    f_data = await get_source()
    source_list = dict(f_data['source_list'])
    if source_name not in source_list:
        return False

    f_data['current'] = source_name
    current_dir = os.path.join(os.path.dirname(__file__), 'data_source.json')
    with open(current_dir, 'w', encoding='UTF-8') as f:
        # noinspection PyTypeChecker
        json.dump(f_data, f, indent=4, ensure_ascii=False)
    return True


# 获取源
async def get_source() -> dict:
    current_dir = os.path.join(os.path.dirname(__file__), 'data_source.json')
    with open(current_dir, 'r', encoding='UTF-8') as af:
        f_data = json.load(af)
    return f_data


# 获取当前的数据源详情
async def get_source_detail(f_data: dict) -> dict:
    current = f_data['current']
    source_list = f_data.get('source_list', {})
    return source_list.get(current, {})


# 通用头
async def get_headers(f_data: dict) -> dict:
    source_detail = await get_source_detail(f_data)
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Custom-Source': 'Kyaru',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
        'Content-Type': 'application/json',
        'Origin': f'https://{source_detail["domain"]}',
        'Referer': f'https://{source_detail["domain"]}/'
    }
    return headers


# 获取最新数据的时间档
async def get_current_time(session: AsyncClient, server: str, f_data: dict) -> str:
    source_detail = await get_source_detail(f_data)
    url = source_detail['api'] + '/current/getalltime/tw'
    time_tmp = await session.get(url, headers=await get_headers(f_data), timeout=10)
    alltime = time_tmp.json()
    all_days = alltime['data'][server].keys()
    up_day = list(all_days)[-1]
    up_hour = list(alltime['data'][server][up_day])[-1]
    up_time = str(up_day) + str(up_hour)
    return up_time


# 返回查询信息
async def get_search_rank(session: AsyncClient, server: str, uptime: str, f_data: dict, search_type: str = None, search_param: str = '') -> dict:
    source_detail = await get_source_detail(f_data)
    url = source_detail['api'] + '/search/' + search_type
    file_tmp = 'tw/' + str(server) + '/' + str(uptime)
    params = {
        'filename': file_tmp,
        'search': search_param,
        'page': 0,
        'page_limit': 10
    }
    clan_score_tmp = await session.post(url, headers=await get_headers(f_data), json=params, timeout=10)
    clan_score = clan_score_tmp.json()
    return clan_score


# 生成图片
async def create_img(info_data: dict, filename_tmp: str, is_all: bool):
    raw_data = {
        'title': 'PCR台服会战档线',
        'index_column': 'rank',
        'show_columns': {
            'rank': '排名',
            'clan_name': '公会名',
            'member_num': '人数',
            'leader_name': '会长名',
            'damage': '分数',
            'lap': '等效周目',
            'grade_rank': '上期排名'
        }
    }
    if is_all:
        raw_data['index_column'] = 'all_server_rank'
        raw_data['show_columns']['all_server_rank'] = '全服排名'

    # 输入参数
    data_list = []
    for _id in info_data['data'].keys():
        rank = info_data['data'][str(_id)]['rank']
        clan_name = info_data['data'][str(_id)]['clan_name']
        # 去除特殊字符，只保留中英日韩数字
        clan_name = re.sub(
            u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a\uAC00-\uD7AF\u3040-\u31FF])",
            "",
            clan_name
        )
        member_num = str(info_data['data'][str(_id)]['member_num']).replace('.0', '')
        leader_name = info_data['data'][str(_id)]['leader_name']
        # 去除特殊字符，只保留中英日韩数字
        leader_name = re.sub(
            u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a\uAC00-\uD7AF\u3040-\u31FF])",
            "",
            leader_name
        )
        damage = info_data['data'][str(_id)]['damage']
        lap = info_data['data'][str(_id)]['lap']
        grade_rank = str(info_data['data'][str(_id)]['grade_rank']).replace('.0', '')

        data = {
            'rank': rank,
            'clan_name': clan_name,
            'member_num': str(member_num) + '人',
            'leader_name': leader_name,
            'damage': damage,
            'lap': str(lap) + '周目',
            'grade_rank': grade_rank,
        }

        if is_all:
            all_server_rank = str(info_data['data'][str(_id)]['all_server_rank'])
            data['all_server_rank'] = all_server_rank

        data_list.append(data)

    raw_data['data_list'] = data_list

    # 生成并保存图片
    fig = await create_table(raw_data)
    await save_fig_as_image(fig, os.path.join(image_dir, filename_tmp))
