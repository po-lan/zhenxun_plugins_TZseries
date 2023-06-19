import re

from nonebot.rule import to_me

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from utils.utils import is_number
from utils.message_builder import image
from utils.image_utils import text2image
from models.bag_user import BagUser
from configs.config import NICKNAME, Config
import random
from ._model import TZtreasury

__zx_plugin_name__ = "刮刮乐"
__plugin_usage__ = f"""
usage：
    {NICKNAME}是庄家
    指令：
    @{NICKNAME} 刮刮乐 ?[数量]
    {NICKNAME}刮刮乐 ?[数量]
    管理员命令：
        刮刮乐倍率 num>0.1
        刮刮乐购买量 num>=1
        刮刮乐奖池选择 id>=-1
        刮刮乐奖池查看 
""".strip()
__plugin_des__ = "堂主小赌场-刮刮乐"
__plugin_cmd__ = ["刮刮乐 ?[数量]"]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
# 开发的时候和某痕聊了很多
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["刮刮乐"],
}
__plugin_cd_limit__ = {
    "cd": 10,
    "limit_type": "user",
    "rst": None,
}
__plugin_configs__ = {
    "level": {
        "value": -1,
        "help": "奖池等级，-1为自动",
        "default_value": -1
    },
    "maxNum": {
        "value": 50,
        "help": "单次最大购买量",
        "default_value": 50
    },
    "Magnification": {
        "value": 1,
        "help": "金币倍率",
        "default_value": 1
    }
}

ggl = on_command("刮刮乐", priority=5, block=True, rule=to_me())


@ggl.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    num = 1
    maxNum = Config.get_config("TZggl", "MAXNUM") or 50
    setJackpotLevel = Config.get_config("TZggl", "LEVEL") or -1
    Magnification = Config.get_config("TZggl", "MAGNIFICATION") or 1
    if is_number(msg) and int(msg) > 0:
        num = int(msg) if int(msg) <= maxNum else maxNum
    uid = event.user_id
    gid = event.group_id

    # 判断 钱是否够用
    cost = 100 * Magnification * num
    xgold = await BagUser.get_gold(uid, gid)
    if xgold < cost:
        await ggl.finish(
            f"\n金币不够还想买刮刮乐？\n您的金币余额为{str(await BagUser.get_gold(event.user_id, event.group_id))} \n刮刮乐cd: 10秒",
            at_sender=True)

    # allLotteryGold = await TZlottery.getLotteryGold(gid) + int(cost*0.7)
    allLotteryGold = await TZtreasury.get_group_treasury(gid) + int(cost * 0.7)
    await TZtreasury.update_treasury_info(group_id=gid, num=int(cost * 0.2))

    await BagUser.spend_gold(uid, gid, cost)
    text = f"花费{cost}金币购买{num}张刮刮乐\n刮开刮刮乐\n"
    rl = p_random([0, 1, 2, 3, 4, 5, 6, 7, 8], p, num)

    sa = []
    spend = True
    # 计算每一档奖金
    for index, Jackpot in enumerate(Jackpot_Values):
        sa.append(0)
        for i in rl:
            if i > 0:
                sa[index] += Jackpot[i - 1] * Magnification
        # sa[index] = sa[index] * 3
        # 判读每档是否够用
        sa[index] = 1 if sa[index] * 3 * (30 / num) < allLotteryGold - 200 else 0

    # 如果连0.1的期望都不够 那就不消耗金库
    if max(sa) == 0:
        spend = False

    # 档位
    level = sa.index(1) if max(sa) == 1 else len(Jackpot_Values) - 1
    if setJackpotLevel != -1:
        level = setJackpotLevel
    elif level != len(Jackpot_Values) - 1:
        level = random.randint(level, len(Jackpot_Values) - 1)

    # 调试用
    # text += f"当前档位：{level}\n"

    allGet = 0
    b = {}
    for i in rl:
        b[i] = (b[i] + 1) if i in b else 1

    # 防止 特等奖 超过2次
    if 0 in b and b[0] > 2:
        more = 2 - b[0]
        b[0] = 2
        # 超过的量当作谢谢惠顾
        if 8 in b:
            b[8] += more
        else:
            b[8] = more

    for i in sorted(b.keys()):
        text += f"{Plevel[i]}:{b[i]}次  ("
        if i == 0:
            allGet += int(20 * b[i] * allLotteryGold / 100)
            text += f"Wow你拿走了 福利金库中的({20 * b[i]})%({int(20 * b[i] * allLotteryGold / 100)})\n"
        else:
            allGet += int(Jackpot_Values[level][i - 1] * Magnification * b[i])
            text += f"{int(Jackpot_Values[level][i - 1] * Magnification * b[i])})\n"

    text += f"\n共得到{allGet}金币\n纳税{int(allGet * 0.1)}金币(10%)"

    if spend:
        # await TZlottery.setLotteryGold(gid, allLotteryGold - allGet)
        await TZtreasury.update_treasury_info(gid, - allGet)
    if int(allGet * 0.1) != 0:
        await TZtreasury.update_treasury_info(group_id=gid, num=int(allGet * 0.1))
    if int(allGet * 0.9) != 0:
        await BagUser.add_gold(uid, gid, int(allGet * 0.9))

    await ggl.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()),at_sender=True)


# 倍率调整
Magnification = on_command(
    "刮刮乐倍率", priority=5, permission=SUPERUSER, block=True)


@Magnification.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if is_number(msg) and float(msg) > 0.1:
        Config.set_config("TZggl", "MAGNIFICATION", float(msg))
        await Magnification.finish(f"倍率成功设置为{float(msg)}倍", at_sender=True)
    else:
        await Magnification.finish(f"参数只能为数字且不为空且大于0.1", at_sender=True)


# 单次最大购买量调整
maxNum = on_command("刮刮乐购买量", priority=5, permission=SUPERUSER, block=True)


@maxNum.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if is_number(msg) and int(msg) > 0:
        Config.set_config("TZggl", "MAXNUM", int(msg))
        await maxNum.finish(f"最大购买量成功设置为{int(msg)}张", at_sender=True)
    else:
        await maxNum.finish(f"参数只能为数字且不为空", at_sender=True)


# 奖池调整
level = on_command("刮刮乐奖池选择", priority=5, permission=SUPERUSER, block=True)


@level.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if is_number(msg) and int(msg) >= -1:
        if int(msg) < len(Jackpot_Values):
            Config.set_config("TZggl", "LEVEL", int(msg))
            await level.finish(f"奖池已调整", at_sender=True)
        else:
            await level.finish(f"你的输入有问题\n最小为-1\最大为{len(Jackpot_Values) - 1}", at_sender=True)
    else:
        await level.finish(f"参数只能为数字且不为空", at_sender=True)


# 奖池显示
levelShow = on_command("刮刮乐奖池查看", priority=5, permission=SUPERUSER, block=True)


@levelShow.handle()
async def _(arg: Message = CommandArg()):
    le = Config.get_config("TZggl", "LEVEL")
    if le == -1:
        text = f"当前回本期望： 自动\n"
    else:
        text = f"当前回本期望： {list(Jackpots.keys())[le]}\n"

    text += "刮刮乐所有奖池回本期望：\n\n"
    text += f"id:-1  期望：自动调节\n"
    for i, v in enumerate(Jackpots.keys()):
        text += f"id:{i}  期望：{v}\n"

    text += "\n例：刮刮乐奖池选择 -1"

    await level.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()))


# words
Plevel = ["特等奖", "一等奖", "二等奖", "三等奖", "四等奖", "五等奖", "六等奖", "七等奖", "谢谢惠顾"]


def p_random(s, p, size: int = 1):
    assert len(s) == len(p), "Length does not match."
    assert size >= 1, "size must >=1."
    assert sum(p) == 1, "Total rate is not 1."

    rlist = []

    for b in range(size):
        sup_list = [len(str(i).split(".")[-1]) for i in p]
        top = 10 ** max(sup_list)
        new_rate = [int(i * top) for i in p]
        rate_arr = []
        for i in range(1, len(new_rate) + 1):
            rate_arr.append(sum(new_rate[:i]))
        rand = random.randint(1, top)
        data = None
        for i in range(len(rate_arr)):
            if rand <= rate_arr[i]:
                data = s[i]
                break

        rlist.append(data)

    # return rlist if len(rlist) > 1 else rlist[0]
    return rlist


# 概率
p = [
    7.13770779651823E-06, 0.00428262467791094,
    0.0178442694912956, 0.0356885389825911,
    0.0713770779651823, 0.0999279091512552,
    0.128478740337328, 0.256957480674656,
    0.385436221011984 + 4.440892098500626e-16
]
# 奖池
Jackpots = {
    # 期望2.002098456135840
    2.0: [1000, 700, 600, 450, 400, 300, 200, 0],
    # 期望1.500182008950560
    1.5: [3000, 900, 500, 400, 300, 200, 75, 0],
    # 期望0.900045680351739
    0.9: [1600, 800, 550, 300, 150, 80, 10, 0],
    # 期望64.994575458231000
    0.65: [560, 500, 300, 200, 120, 70, 30, 0],
    # 期望0.400059955461657
    0.4: [300, 250, 200, 150, 55, 35, 25, 0],
    # 期望.10003283275281200
    0.1: [115, 95, 45, 30, 15, 10, 5, 0]
}
Jackpot_Values = list(Jackpots.values())



