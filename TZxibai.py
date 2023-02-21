from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from models.bag_user import BagUser
from ._model import TZtreasury, TZBlack
from utils.utils import scheduler
import random

__zx_plugin_name__ = "洗白"
__plugin_usage__ = """
usage：
    用于打完劫后把钱弄出来
    不洗白的话超过24小时会被警察追回
    洗白的cd为18h
    指令：
    #洗白
    #我的黑钱
""".strip()
__plugin_des__ = "洗白小钱钱"
__plugin_cmd__ = ["洗白", "#洗白", "#我的黑钱"]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 0.1
__plugin_author__ = "弘崕"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["洗白", "#洗白", "#我的黑钱"]

}


# 黑钱超出24h自动追回
@scheduler.scheduled_job(
    "interval",
    seconds=30,
)
async def _():
    await zh()


xb = on_command("#洗白", priority=5, block=True)
hq = on_command("#我的黑钱", priority=5, block=True)


@xb.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    uid = event.user_id
    # 获取 没有洗白 且没过期的黑钱
    My24H_isBlock = await TZBlack.get_my_today_all_isBlock(uid, gid)

    if My24H_isBlock == 0:
        await xb.finish("你并没有什么值得洗白的", at_sender=True)

    if await TZBlack.before_Time_Has(uid, gid):
        await xb.finish("再等等吧，过会再洗吧", at_sender=True)

    # 分开
    MList = []

    while (My24H_isBlock > 0):
        if My24H_isBlock >= 50:
            MList.append(50)
            My24H_isBlock -= 50
        else:
            MList.append(My24H_isBlock)
            My24H_isBlock = 0

    Success = 0
    unSuccess = 0

    # 洗白
    for x in MList:
        if random.randint(1, 10) > 6:
            Success += x
        else:
            unSuccess += x

    # 成功洗白存入
    await BagUser.add_gold(uid, gid, Success)
    # 失败的存入 金库
    await TZtreasury.update_treasury_info(gid, int(unSuccess * 0.5))
    # 打洗白结束标记
    await TZBlack.all_toW(uid, gid)

    text = f"本次成功洗白了：{Success}金币\n洗白失败的50%已存入金库"
    await xb.finish(text, at_sender=True)


@hq.handle()
async def _(event: GroupMessageEvent):
    gid = event.group_id
    uid = event.user_id
    # 获取 没有洗白 且没过期的黑钱
    My24H_isBlock = await TZBlack.get_my_today_all_isBlock(uid, gid)
    text = f"当前还有{My24H_isBlock}未洗白\n18h才能洗白一次哦"
    await xb.finish(text, at_sender=True)


# 超过24h 未洗白自动追回
async def zh():
    # 获取可以进行追回的钱
    Blist = await TZBlack.Over24_block_money()
    for x in Blist:
        await BagUser.add_gold(x.from_qq, x.gid, x.money)
        # 追回后进行标记
        await TZBlack.Over24_block_isBack(x.id)
