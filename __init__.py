import asyncio
import json
import os

from httpx import AsyncClient

from yuiChyan.exception import LakePermissionException, CommandErrorException, FunctionException
from yuiChyan.http_request import get_session_or_create, close_async_session
from yuiChyan.permission import check_permission, SUPERUSER, ADMIN
from yuiChyan.service import Service
from .lock import lock_clan, select_all_clan, unlock_clan, judge_lock, current_dir
from .search import set_source, get_source, get_current_time, create_img, get_search_rank, image_dir

sv = Service('clan_rank_tw', help_cmd='会战排名帮助')


# 选择数据源
@sv.on_prefix('选择会战数据源')
async def select_source(bot, ev):
    if not check_permission(ev, SUPERUSER):
        raise LakePermissionException(ev, '选择数据源功能仅限维护组')

    source_name = str(ev.message).strip()
    success = await set_source(source_name)
    msg = f'当前数据源成功切换至：{source_name}' if success else f'失败！数据源{source_name}未在[data_source.json]中配置'
    await bot.send(ev, msg)


# 查看数据源
@sv.on_match('查看会战数据源')
async def view_source(bot, ev):
    f_data = await get_source()
    msg = f'当前选择的数据源是：{f_data["current"]}'
    await bot.send(ev, msg)


# 查档线
@sv.on_prefix('查档线')
async def search_line(bot, ev):
    server = str(ev.message).strip()
    if server not in ['1', '2']:
        raise CommandErrorException(ev, '服务器编号错误！(可选值有：1/2)')

    f_data = await get_source()

    session: AsyncClient = get_session_or_create('ClanRankTWLine', True)
    up_time = await get_current_time(session, server, f_data)
    filename_tmp = 'tw-' + str(server) + '-' + str(up_time) + '-' + 'scoreline' + '.png'
    await asyncio.sleep(0.5)

    image_path = os.path.join(image_dir, filename_tmp)
    if not os.path.isfile(image_path):
        score_line = await get_search_rank(session, server, up_time, f_data, 'scoreline')
        if score_line['state'] != 'success':
            raise FunctionException(ev, '查询数据失败，接口返回失败！')
        await create_img(score_line, filename_tmp, False)
    else:
        sv.logger.info(f'将直接发送已有缓存图片 [{filename_tmp}]')
    await close_async_session('ClanRankTWLine', session)

    line_img = f'[CQ:image,file=file:///{image_path}]'
    formatted_datetime = f"{up_time[:4]}-{up_time[4:6]}-{up_time[6:8]} {up_time[8:10]}:{up_time[10:]}"
    msg = f'> 台服 {server}服 档线如下：\n时间：{formatted_datetime}\n{line_img}'
    await bot.send(ev, msg)


# 按 公会名 查询排名
@sv.on_prefix('查公会')
async def search_clan(bot, ev):
    await query('公会', 'clan_name', bot, ev)


# 按 会长名 查询排名
@sv.on_prefix('查会长')
async def search_leader(bot, ev):
    await query('会长', 'leader_name', bot, ev)


# 按 排名 查询公会
@sv.on_prefix('查排名')
async def search_rank(bot, ev):
    await query('排', 'rank', bot, ev)


# 实际查询逻辑
async def query(search_type, search_type_code, bot, ev):
    all_text = str(ev.message).strip()
    info_tmp = all_text.split(' ', 1)
    server = info_tmp[0]
    search_name = info_tmp[1]
    if server not in ['1', '2', 'all']:
        raise CommandErrorException(ev, '服务器编号错误！(可选值有：1/2/all)')

    is_all = True if server == 'all' else False
    server = 'merge' if server == 'all' else server
    f_data = await get_source()

    session: AsyncClient = get_session_or_create('ClanRankTWQuery', True)
    up_time = await get_current_time(session, server, f_data)
    filename_tmp = 'tw-' + str(server) + '-' + str(up_time) + '-' + str(search_name) + '.png'
    await asyncio.sleep(0.5)

    image_path = os.path.join(image_dir, filename_tmp)
    if not os.path.isfile(image_path):
        clan_score = await get_search_rank(session, server, up_time, f_data, search_type_code, search_name)
        if clan_score['state'] != 'success':
            raise FunctionException(ev, '出现异常，请尝试重新输入命令！')
        if clan_score['total'] == 0:
            raise FunctionException(ev, f'未查询到信息，请确保输入{search_type}名[{search_name}]正确！')
        await create_img(clan_score, filename_tmp, is_all)
    else:
        sv.logger.info(f'将直接发送已有缓存图片 [{filename_tmp}]')
    await close_async_session('ClanRankTWQuery', session)

    clan_img = f'[CQ:image,file=file:///{image_path}]'
    formatted_datetime = f"{up_time[:4]}-{up_time[4:6]}-{up_time[6:8]} {up_time[8:10]}:{up_time[10:]}"
    server = '全' if server == 'merge' else server
    msg = f'台服 {server}服 {search_type}名查询 “{search_name}” 结果如下：\n时间：{formatted_datetime}\n{clan_img}'
    await bot.send(ev, msg)


# 绑定公会
@sv.on_prefix('绑定公会')
async def locked_clan(bot, ev):
    if check_permission(ev, ADMIN):
        raise LakePermissionException(ev, '绑定功能仅限群主和管理员')

    group_id = str(ev.group_id)
    all_text = str(ev.message).strip()
    info_tmp = all_text.split(' ', 1)
    server = info_tmp[0]
    clan_name = info_tmp[1]
    if server not in ['1', '2']:
        raise CommandErrorException(ev, '服务器编号错误！(可选值有：1/2)')

    f_data = await get_source()

    session: AsyncClient = get_session_or_create('ClanRankTWBind', True)
    up_time = await get_current_time(session, server, f_data)
    await asyncio.sleep(0.5)

    clan_score = await get_search_rank(session, server, up_time, f_data, 'clan_name', clan_name)
    await close_async_session('ClanRankTWBind', session)

    if clan_score['state'] != 'success':
        raise FunctionException(ev, '出现异常，请尝试重新输入命令！')

    if clan_score['total'] == 0:
        msg = '未查询到公会，请确保公会名正确！'
    elif clan_score['total'] == 1:
        msg, flag = await judge_lock(group_id)
        if flag:
            msg += f'\n因此请勿重复绑定'
            await bot.send(ev, msg)
            return
        msg = await lock_clan(server, clan_name, group_id)
    else:
        msg = await select_all_clan(clan_score)
        msg += '\n\n该功能需精确的公会名，因此请尝试重新输入命令！'
    await bot.send(ev, msg)


# 解绑公会
@sv.on_match('解绑公会')
async def unlocked_clan(bot, ev):
    if check_permission(ev, ADMIN):
        raise LakePermissionException(ev, '解绑功能仅限群主和管理员')

    group_id = ev['group_id']
    msg, flag = await judge_lock(group_id)
    if not flag:
        msg += f'\n因此请先绑定公会'
        await bot.send(ev, msg)
        return
    msg = await unlock_clan(group_id)
    await bot.send(ev, msg)


# 查看公会绑定状态
@sv.on_match('查询公会绑定')
async def lock_status(bot, ev):
    group_id = str(ev['group_id'])
    msg, flag = await judge_lock(group_id)
    await bot.send(ev, msg)


# 适用于绑定公会后的查询排名信息
@sv.on_match('公会排名')
async def search_locked(bot, ev):
    group_id = str(ev['group_id'])
    msg, flag = await judge_lock(group_id)
    if not flag:
        msg += f'\n因此请先绑定公会'
        await bot.send(ev, msg)
        return

    with open(current_dir, 'r', encoding='UTF-8') as af:
        config_data = json.load(af)
    server = config_data[group_id]['server']
    clan_name = config_data[group_id]['clan_name']

    f_data = await get_source()

    session: AsyncClient = get_session_or_create('ClanRankTWQuerySelf', True)
    up_time = await get_current_time(session, server, f_data)
    await asyncio.sleep(0.5)

    info_data = await get_search_rank(session,  server, up_time, f_data, 'clan_name', clan_name)
    await close_async_session('ClanRankTWQuerySelf', session)

    clan_list = dict(info_data['data'])
    if not clan_list:
        raise FunctionException(ev, f'无法查询到本群绑定的公会[{clan_name}]')

    rank_list = list(clan_list.keys())
    clan = clan_list.get(rank_list[0], {})

    rank = clan['rank']
    clan_name = clan['clan_name']
    member_num = str(clan['member_num']).replace('.0', '')
    leader_name = clan['leader_name']
    damage = clan['damage']
    lap = clan['lap']
    grade_rank = str(clan['grade_rank']).replace('.0', '')

    formatted_datetime = f"{up_time[:4]}-{up_time[4:6]}-{up_time[6:8]} {up_time[8:10]}:{up_time[10:]}"
    msg = f'公会名：{clan_name}\n时间：{formatted_datetime}\n排名：{rank}'
    msg += f'\n会长名：{leader_name}\n人数：{member_num}人\n分数：{damage}'
    msg += f'\n等效周目：{lap}周目\n上期排名：{grade_rank}'
    await bot.send(ev, msg)
