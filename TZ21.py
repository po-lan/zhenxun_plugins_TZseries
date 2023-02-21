import time
import random
from nonebot import on_command
from nonebot.rule import to_me
from models.bag_user import BagUser
from nonebot.params import CommandArg
from utils.message_builder import image
from utils.image_utils import text2image
from nonebot.permission import SUPERUSER
from configs.config import NICKNAME, Config
from utils.utils import is_number, UserBlockLimiter, scheduler
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent, Message, MessageSegment
from ._model import TZtreasury

__zx_plugin_name__ = "21点"
__plugin_usage__ = f"""
usage：
    第一位玩家发起活动，指令：@{NICKNAME} 21点[金币数量]
    接受21点赌局，指令：入场[金币数量]
    人齐后开局，指令：开局
    拿牌指令：拿牌
    宣布停止，指令：停牌（此指令无反馈）
    所有人停牌，或者超时90s后，结算指令：21点(结算/结束)
    {NICKNAME} 必要点数17
    起手2牌合计21点为黑杰克，比其他21点大
    获胜奖励为胜者按各自入场费
    如果{NICKNAME}没钱了，就不会再玩了
    当然你可以输入 [21点打钱 金币数量] 给机器人打钱
""".strip()
__plugin_des__ = f"{NICKNAME}小赌场-21点"
__plugin_cmd__ = ["21点 [金币数量]/继续/21点结算"]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["21点"],
}

__plugin_configs__ = {
    "FC": {
        "value": True,
        "name": "流水控制",
        "help": "通过算牌等 使群内不会使用21点刷钱过快",
        "default_value": True
    },
    "CHANCE": {
        "value": 3,
        "help": "0-10;0为关",
        "name": "开局前随机换牌概率",
        "default_value": 3
    }
}

Ginfo = {}
blk = UserBlockLimiter()


def getStartUserName(gid):
    global Ginfo
    return Ginfo[gid]["players"][Ginfo[gid]["startUid"]]["uname"]


# 定时刷新
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=1,
)
async def _():
    await upadte_gold()


dq = on_command("21点打钱", priority=5, block=True)

opendian = on_command("21点", priority=5, block=True,rule=to_me())

ruchang = on_command("入场", priority=5, block=True)

kaiju = on_command("开局", priority=5, block=True)

napai = on_command("拿牌", priority=5, block=True)

tingpai = on_command("停牌", priority=5, block=True)

jiesuan = on_command("21点结算", aliases={"21点结束"}, priority=5, block=True)

super_end = on_command("21点强制结算", aliases={"21点强制结束"}, priority=5, permission=SUPERUSER, block=True)

FC = on_command("21点流水控制", priority=5, permission=SUPERUSER, block=True)

chance = on_command("开局前随机换牌概率", priority=5, permission=SUPERUSER, block=True)

update = on_command("更新21点金币", priority=5, permission=SUPERUSER, block=True)


@super_end.handle()
async def _(event: GroupMessageEvent):
    global Ginfo
    if Ginfo[event.group_id]["players"] and Ginfo[event.group_id]["state"] != 0:
        for v in Ginfo[event.group_id]["players"].values():
            if v['uid'] != 0 and not v['banker']:
                await BagUser.add_gold(v['uid'], event.group_id, v['cost'])
        Ginfo[event.group_id]["state"] = 0
        await super_end.finish("对局已强制结算，金币已退回")
    else:
        await super_end.finish("当前没有对局")


@dq.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    gid = event.group_id
    uid = event.user_id
    if blk.check(gid):
        await dq.finish()
    blk.set_true(gid)
    msg = arg.extract_plain_text().strip()
    if msg:
        if is_number(msg) and int(msg) > 0:
            cost = int(msg)
            if await BagUser.get_gold(uid, gid) < cost:
                blk.set_false(gid)
                await dq.finish(f"你都没那些钱就不要给{NICKNAME}打钱了", at_sender=True)
            else:
                blk.set_false(gid)
                await BagUser.spend_gold(uid, gid, cost)
                Ginfo[gid]["gold"] += cost

                if Ginfo[gid]["gold"] > -14514:
                    await dq.finish(f"这些钱够{NICKNAME}再玩一会的了", at_sender=True)
                else:
                    await dq.finish(f"这些钱够{NICKNAME}收下了，不过{NICKNAME}还要接着去打工", at_sender=True)

        else:
            blk.set_false(gid)
            await dq.finish(f"打钱的金额为数字且需要大于0哦", at_sender=True)
    else:
        blk.set_false(gid)
        await dq.finish(f"如果你是要给{NICKNAME}打钱记得带上金额啊", at_sender=True)


@opendian.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    gid = event.group_id
    uid = event.user_id
    if blk.check(gid):
        await opendian.finish()
    blk.set_true(gid)

    global Ginfo
    # 获取用户名
    uname = event.sender.card if event.sender.card else event.sender.nickname
    # 判断上一场是否结束
    if gid in Ginfo:
        # 有这个群的数据
        if Ginfo[gid]["state"] != 0:
            blk.set_false(gid)
        if Ginfo[gid]["state"] == 1:
            # state : 已开场，未开局
            await opendian.finish(f"上一场21点还未开始，请输入入场\n")
        if Ginfo[gid]["state"] == 2:
            # state : 已开局，未结束
            await opendian.finish(f"上一场21点还未结束，请等待\n")
    # 玩家是否为庄
    banker = False
    msg = arg.extract_plain_text().strip().split()
    # 判断入场赌注
    if msg:
        if is_number(msg[0]) and int(msg[0]) > 0:
            cost = int(msg[0])
            if cost > 10000:
                blk.set_false(gid)
                await opendian.finish(f"{NICKNAME}不接受10000以上的赌注哦", at_sender=True)
            if cost < 20:
                blk.set_false(gid)
                await opendian.finish(f"{NICKNAME}觉得20以下的赌注不得劲哎", at_sender=True)
        else:
            blk.set_false(gid)
            await opendian.finish(f"赌注是数字啊喂", at_sender=True)
        if len(msg) == 2:
            if msg[1] == '庄':
                banker = True
            else:
                await opendian.finish(f"参数错误，请查看帮助后重试", at_sender=True)
    else:
        blk.set_false(gid)
        await opendian.finish(f"没有获取到参数，请查看帮助后重试", at_sender=True)

    # 输多了 就摆烂
    if gid in Ginfo and -14514 > Ginfo[gid]["gold"]:
        await opendian.finish(f"{NICKNAME}输的有点多了，{NICKNAME}去打工赚钱陪你们玩")

    # 判断 是否够用
    user_gold = await BagUser.get_gold(uid, gid)
    if user_gold < cost:
        blk.set_false(gid)
        await opendian.finish(f"\n金币不够还想来21点？\n您的金币余额为{str(await BagUser.get_gold(uid, gid))}", at_sender=True)
    if user_gold < 100 and banker:
        await opendian.finish(f"\n庄家至少需要100余额\n您的金币余额为{str(await BagUser.get_gold(uid, gid))}", at_sender=True)
    if gid not in Ginfo:
        Ginfo[gid] = {"gold": 0, "state": 1}

    Ginfo[gid]["players"] = {}
    Ginfo[gid]["state"] = 1
    Ginfo[gid]["initCost"] = cost
    Ginfo[gid]["startUid"] = uid
    Ginfo[gid]["freeCard"] = []
    Ginfo[gid]["time"] = time.time()
    Ginfo[gid]["banker"] = banker
    await ruchangx(gid, uid, uname, cost, banker)
    blk.set_false(gid)
    if banker:
        await opendian.finish(f'{uname}发起了一场21点挑战\n{uname}为庄家入场')
    await opendian.finish(f'{uname}发起了一场21点挑战\n{uname}已自动入场')


@ruchang.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    gid = event.group_id
    uid = event.user_id
    # 阻断 防止触发过快
    if blk.check(gid):
        await ruchang.finish()
    blk.set_true(gid)

    # 判断上一场是否结束
    if gid in Ginfo:
        # 有这个群的数据
        if Ginfo[gid]["state"] == 0:
            # state : 未开场
            blk.set_false(gid)
            await opendian.finish(f"请先开场、开场后会自动入场")
        if Ginfo[gid]["state"] == 2:
            # state : 已开局，未结束
            blk.set_false(gid)
            await opendian.finish(f"上一场21点还未结束，请等待")
    else:
        # 没有本群数据
        blk.set_false(gid)
        await opendian.finish(f"请先开场、开场后会自动入场")

    # 人数判断
    if len(Ginfo[gid]["players"]) > 5:
        blk.set_false(gid)
        await ruchang.finish(f"人太多啦，{NICKNAME}不行啦")

    # 判断是否已经入场
    if uid in Ginfo[gid]["players"]:
        blk.set_false(gid)
        await ruchang.finish(f"你已入场，请勿重复操作")

    # 判断入场赌注
    msg = arg.extract_plain_text().strip()
    if msg:
        if is_number(msg) and int(msg) > 0:
            cost = int(msg)
            if cost > 10000:
                blk.set_false(gid)
                await ruchang.finish(f"{NICKNAME}不接受10000以上的赌注哦", at_sender=True)
            if cost < 20:
                blk.set_false(gid)
                await ruchang.finish(f"{NICKNAME}觉得20以下的赌注不得劲哎", at_sender=True)
        else:
            blk.set_false(gid)
            await ruchang.finish(f"赌注是数字啊喂", at_sender=True)
    else:
        blk.set_false(gid)
        await ruchang.finish(f"请输入你的赌注", at_sender=True)

    if await BagUser.get_gold(uid, gid) < cost:
        blk.set_false(gid)
        await ruchang.finish(f"\n金币不够还想来21点？\n您的金币余额为{str(await BagUser.get_gold(uid, gid))}", at_sender=True)
    # 检验赌注金额
    if cost < (Ginfo[gid]["initCost"] / 2) or cost > (Ginfo[gid]["initCost"] * 2):
        blk.set_false(gid)
        await ruchang.finish(f"赌注不得小于开局玩家的1/2或大于开局玩家的两倍", at_sender=True)

    uname = event.sender.card if event.sender.card else event.sender.nickname
    blk.set_false(gid)
    await ruchangx(gid, uid, uname, cost)
    # await ruchang.send("你已入场，请等待开局",at_sender = True)

    text = f'你已加入 {getStartUserName(gid)} 创建的21点游戏\n全部已入场的玩家：'
    for user in Ginfo[gid]["players"].values():
        text += f'\n\t·{user["uname"]}'

    # 发送
    await ruchang.send(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()), at_sender=True)


# 入场 记录
async def ruchangx(gid: int, uid: int, uname: str, cost: int, banker: bool = False):
    global Ginfo
    Ginfo[gid]["players"][uid] = {
        "uname": uname,
        "cost": cost,
        "BJ": False,
        "uid": uid,
        "banker": banker
    }
    Ginfo[gid]["time"] = time.time()
    if not banker:
        await BagUser.spend_gold(uid, gid, cost)


# 开局
@kaiju.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    gid = event.group_id
    uid = event.user_id
    # 判断上一场是否结束
    if gid in Ginfo:
        # 有这个群的数据
        if Ginfo[gid]["state"] == 0:
            # state : 未开场
            await opendian.finish(f"请先开场、开场后等待他人入场结束后在输入")
        if Ginfo[gid]["state"] == 2:
            # state : 已开局，未结束
            await opendian.finish(f"上一场21点还未结束，请等待")
    else:
        # 没有本群数据
        await opendian.finish(f"请先开场、开场后等待他人入场结束后在输入")

    # 判断是不是开场的人发的开局
    if Ginfo[gid]["startUid"] != uid:
        await opendian.finish(f"开局失败\n需由创建者 {getStartUserName(gid)} 开局")
    # 机器人加入游戏
    if not Ginfo[gid]["banker"]:
        Ginfo[gid]["players"][0] = {
            "uid": 0,
            "banker": True,
            "BJ": False,
            "uname": NICKNAME,
            "cost": int(0)
        }
    # 判断是不是开场的人发的开局
    elif len(Ginfo[gid]["players"]) < 2:
        await opendian.finish(f"开局失败\n你要自己跟自己玩嘛")

    # 停止入场
    Ginfo[gid]["state"] = 2

    # 生成牌组，且当牌组为7时重新生成
    Card = sortOut()
    while len(Card) == 7:
        Card = sortOut()

    # 正常模式
    for i, key in enumerate(Ginfo[gid]["players"]):
        Ginfo[gid]["players"][key] = {
            **Card[i], **Ginfo[gid]["players"][key]}

    # 回收空牌
    for v in Card[len(Ginfo[gid]["players"]):]:
        for v in v["list"]:
            Ginfo[gid]["freeCard"].append(v)

    # 初次算点
    for v in Ginfo[gid]["players"].values():
        if getSum(v["list"][:v["show"]]) == 21:
            Ginfo[gid]["players"][v["uid"]]["isEnd"] = True
            Ginfo[gid]["players"][v["uid"]]["BJ"] = True
    text = "现已开局，无法再入场\n"
    for v in Ginfo[gid]["players"].values():
        if v['banker']:
            text += f"\n庄家({v['uname']}) 的牌为：暗牌,{v['list'][0]}"
            text += f"\n已知点数为：{getSum(v['list'][:1])}\n\n"
        else:
            text += f"{v['uname']} 的牌为：{','.join(v['list'][:v['show']])}"
            if v["BJ"]:
                text += " 已BlackJack，"

            text += f"总点数为：{getSum(v['list'][:v['show']])}\n"

    await opendian.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()))


@napai.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    uid = event.user_id
    gid = event.group_id
    # 阻断 防止过快
    if blk.check(gid):
        await napai.finish()
    blk.set_true(gid)
    # 判断上一场是否结束
    if gid in Ginfo:
        # 有这个群的数据
        if Ginfo[gid]["state"] == 0:
            # state : 未开场
            blk.set_false(gid)
            await opendian.finish(f"请先开场、开局后才能拿牌")
        if Ginfo[gid]["state"] == 1:
            # state : 已开局，未结束
            blk.set_false(gid)
            await opendian.finish(f"请先开局、开局后才能拿牌")
    else:
        # 没有本群数据
        blk.set_false(gid)
        await opendian.finish(f"请先开场、开局后才能拿牌")

    # 如果玩家不在列表里
    if uid not in Ginfo[gid]["players"]:
        blk.set_false(gid)
        await opendian.finish(f"无关人员不要捣乱\n")

    if Ginfo[gid]["players"][uid]["isEnd"]:
        blk.set_false(gid)
        await opendian.finish(f"你已停牌\n无法拿牌")

    Ginfo[gid]["time"] = time.time()

    # 拿牌就是多展示一位
    Ginfo[gid]["players"][uid]["show"] += 1
    v = Ginfo[gid]["players"][uid]
    allS = getSum(v['list'][:v['show']])

    text = f'{Ginfo[gid]["players"][uid]["uname"]} 拿到的牌为'
    text += f":\n   {','.join(v['list'][:v['show']])} \n"
    text += f"   总点数为：{allS}"

    if allS == 21:
        text += ";已21点，停牌"
        Ginfo[gid]["players"][uid]["isEnd"] = True
    elif allS > 21:
        text += ";炸了，停牌"
        Ginfo[gid]["players"][uid]["isEnd"] = True

    blk.set_false(gid)
    await napai.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()))


@tingpai.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    uid = event.user_id
    gid = event.group_id
    # 判断 是否已经开局

    if gid in Ginfo:
        if Ginfo[gid]["state"] != 2:
            await tingpai.finish("还没开局呢，停个锤子")
    else:
        await tingpai.finish("你都没开场过，停个锤子")

    # 如果玩家不在列表里
    if uid not in Ginfo[gid]["players"]:
        await tingpai.finish(f"无关人员不要捣乱\n")

    Ginfo[gid]["players"][uid]["isEnd"] = True


@jiesuan.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global Ginfo
    uid = event.user_id
    gid = event.group_id
    # 判断 是否已经开局
    if gid in Ginfo:
        if Ginfo[gid]["state"] != 2:
            await jiesuan.finish("还没开局呢，结束个锤子")
    else:
        await jiesuan.finish("你都没开场过，结束个锤子")

    # 如果玩家不在列表里
    if uid not in Ginfo[gid]["players"] and str(uid) not in list(bot.config.superusers):
        await opendian.finish(f"无关人员不要捣乱\n")

    # 判断是不是开场的人发的开局
    if Ginfo[gid]["startUid"] != uid and str(uid) not in list(bot.config.superusers):
        await opendian.finish(f'结束失败\n需由创建者 {getStartUserName(gid)} 结束')

    # 获取 未停牌 玩家 Uid 列表
    def notEndUser(T):
        notEndUserList = []
        # 超时后可以直接结束
        if time.time() - Ginfo[gid]["time"] > 90:
            return []

        # 遍历每一个玩家
        for v in T:
            # 不需要 发起者 和 机器人本身
            if v["uid"] != 0 and v["uid"] != Ginfo[gid]["startUid"] and v["isEnd"] == False:
                notEndUserList.append(v["uid"])

        # 返回 列表
        return notEndUserList

    notList = notEndUser(Ginfo[gid]["players"].values())

    if len(notList) > 0:
        text = "以下用户未停牌:"

        # 列出用户
        for uid in notList:
            user = Ginfo[gid]["players"][uid]
            text += f'\n·{user["uname"]}({getSum(user["list"][:user["show"]], True)})'

        await jiesuan.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()))

    # 计算结果
    await end(gid)


async def end(gid):
    global Ginfo
    # 获取庄UID
    bankerUid = Ginfo[gid]["startUid"] if Ginfo[gid]["banker"] else 0
    banker_name = Ginfo[gid]["players"][bankerUid]["uname"]
    # 让 庄 的牌先打到17
    while getSum(Ginfo[gid]["players"][bankerUid]["list"][:Ginfo[gid]["players"][bankerUid]["show"]]) < 17:
        Ginfo[gid]["players"][bankerUid]["show"] += 1

    bankerS, bankerBoom, text = 0, False, ""

    def isBOOM(T):
        if T["banker"]:
            return False
        return getSum(T["list"][:T["show"]]) > 21

    def isNotBoom(T):
        if T["banker"]:
            return False
        return getSum(T["list"][:T["show"]]) < 22

    def GetWinUser(T):
        if T["banker"]:
            return False
        s = getSum(T["list"][:T["show"]])
        # 如果 炸了 直接 跳过
        if s > 21:
            return False
        if bankerBoom:
            # 如果 庄 炸了，所有没炸的人，都赢
            return True
        else:
            # 庄 是黑杰克
            if Ginfo[gid]["players"][bankerUid]["BJ"]:
                return False
            else:
                # 如果 庄 和玩家 点数相同 ，且 玩家牌比 庄 少
                if bankerS == s and Ginfo[gid]["players"][bankerUid]["show"] > T["show"]:
                    return True
                else:
                    # 机器人和玩家点数不相同
                    # 黑杰克 或者 比机器人点数大的赢
                    if T["BJ"] or s > bankerS:
                        # 玩家中黑杰克赢
                        # 点数大于机器人的赢
                        return True

    # 先计算炸了的
    for value in list(filter(isBOOM, Ginfo[gid]["players"].values())):
        text += f"{value['uname']}的牌是：{','.join(value['list'][:value['show']])} 炸了\n"

    gold = 0
    # 收集金币0
    for v in list(Ginfo[gid]["players"].values()):
        gold += v["cost"]

    # 计算 玩家 最大的得分
    UserMax = max(
        [0] + [getSum(v['list'][:v['show']]) for v in list(filter(isNotBoom, Ginfo[gid]["players"].values()))])

    # 出千
    if (Ginfo[gid]["gold"] < gold / 2 or len(Ginfo[gid]["players"].values()) > 4) and (
            Config.get_config("TZ21", "FC") and Ginfo[gid]["players"][bankerUid]["BJ"] == False) and bankerUid == 0:

        isNotOK = False

        T1 = Ginfo[gid]["players"][0]["list"][:2]

        if UserMax != 21 and getSum(T1) < 16:
            Ginfo[gid]["freeCard"].append(Ginfo[gid]["players"][0]["list"][2:])
            x = 20 - getSum(T1)
            isNotOK = True
            while isNotOK and x > 1:
                Card = "A" if x == 1 else x
                if Card in Ginfo[gid]["freeCard"]:
                    T1.append(Card)
                    Ginfo[gid]["freeCard"].remove(Card)
                    isNotOK = False
                else:
                    x -= 1

            Ginfo[gid]["players"][0]["list"] = T1
            Ginfo[gid]["players"][0]["show"] = len(T1)

        if getSum(Ginfo[gid]["players"][0]["list"]) < UserMax:
            T1 = Ginfo[gid]["players"][0]["list"][:1]
            T2 = []
            i = 0

            Ginfo[gid]["freeCard"].append(Ginfo[gid]["players"][0]["list"][1:])

            def aNew():
                T2 = list(T1) + random.choices(Ginfo[gid]["freeCard"], k=4)

                showList = 2

                while getSum(T2[:showList]) < 17 and showList <= 5:
                    showList += 1

                T2 = T2[:showList]

                return getSum(T2) < UserMax or getSum(T2) >= 21

            while aNew() and i < 200:
                i += 1
                Ginfo[gid]["players"][0]["list"] = T2
                Ginfo[gid]["players"][0]["show"] = len(T2)

    # 提取没炸的人
    for value in list(filter(isNotBoom, Ginfo[gid]["players"].values())):
        text += f"{value['uname']}的牌是：{','.join(value['list'][:value['show']])}\n"

    # 判断 庄 是炸了还是赢了
    bankerCard = Ginfo[gid]["players"][bankerUid]["list"][:Ginfo[gid]["players"][bankerUid]["show"]]
    bankerCard[0], bankerCard[1] = bankerCard[1], bankerCard[0]
    bankerS = getSum(bankerCard)

    if bankerS < 22:
        text = f"{banker_name}的牌是：{','.join(bankerCard)},总点数为{bankerS}\n" + text
    else:
        text = f"{banker_name}的牌是：{','.join(bankerCard)},总点数为{bankerS}，炸了\n" + text
        bankerBoom = True
        # 计算玩家胜利

    winUsers = list(filter(GetWinUser, Ginfo[gid]["players"].values()))
    if len(winUsers) > 0:
        # 胜利的用户
        text += f'\n本场胜利的：'
        for v in winUsers:
            text += f'\n{v["uname"]} 赢得了 {v["cost"]}金币--税{int(v["cost"] * 0.2)}'
            await TZtreasury.update_treasury_info(gid, int(v["cost"] * 0.2))
            await BagUser.add_gold(v["uid"], gid, int(v["cost"] * 1.8))
            gold -= v["cost"] * 2
    else:
        # 没人胜利
        if bankerUid == 0:
            text += f"{NICKNAME} 收走了全部的金币"
        else:
            pass
            # text += f"但 { NICKNAME } 收了3%作为手续费"

    if bankerUid == 0:
        #  金币 加入累计
        Ginfo[gid]["gold"] += gold
        if gold >= 0:
            text += f"\n{banker_name}本局赚了{gold}金币"
        else:
            text += f"\n{banker_name}本局赔了{abs(gold)}金币"
    else:
        # 玩家庄 对玩家扣钱或加钱
        if gold > 0:
            text += f'{banker_name}收走了全部的金币'
            text += f"但 {NICKNAME} 收了5%作为手续费"
            await BagUser.add_gold(bankerUid, gid, int(gold * 0.95))
            await TZtreasury.update_treasury_info(gid, int(gold * 0.05))
        elif gold < 0:
            text += f'{banker_name} 赔付了全部的金币'
            await BagUser.spend_gold(bankerUid, gid, abs(gold))

    #  await jiesuan.send_msg(message=image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()),group_id=gid)

    # 恢复状态
    Ginfo[gid]["state"] = 0

    await jiesuan.finish(message=image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()),
                         group_id=gid)


# 控制部分

# 流水控制
@FC.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg == "开":
        Config.set_config("TZ21", "FC", True)
        await FC.finish(f"流水控制已开启", at_sender=True)
    elif msg == "关":
        Config.set_config("TZ21", "FC", False)
        await FC.finish(f"流水控制已关闭", at_sender=True)
    else:
        await FC.finish(f"参数只能为开或关", at_sender=True)


# 奖池调整
@chance.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if is_number(msg) and int(msg) > -1:
        if int(msg) < 11:
            Config.set_config("TZ21", "CHANCE", int(msg))
            await chance.finish(f"概率已调整为{int(msg) * 10}%", at_sender=True)
        else:
            await chance.finish(f"你的输入有问题\n最小为0最大为10", at_sender=True)
    else:
        await chance.finish(f"参数只能为数字且不为空", at_sender=True)


# 生成初始牌组
def startCard():
    card = [
        'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K',
        'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K',
        'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K',
        'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'
    ]
    random.shuffle(card)
    index = 0
    uid = 0
    run = True

    T0 = {}

    # 生成 牌序
    while run:
        isNotOK = True
        if (index + 2 >= 52):
            run = False
            break
        T1 = card[index:2]
        index += 2
        while isNotOK:
            # 到21了
            if getSum(T1) >= 21:
                isNotOK = False
                T0[uid] = T1
                uid += 1
            else:
                # 没到21就开始选下一个
                T1.append(card[index])
                index += 1
                # 如果牌不够了就停
                if len(card) == index:
                    run = False
                    break

    return T0


# 计算列表和
def getSum(Tl, sumAll=True):
    result = 0

    def aSave(T, result):
        numAces = T.count("A")
        while result > 21 and numAces > 0:
            result -= 10
            numAces -= 1
        return result

    if sumAll:
        result = sum([getNumber(v) for v in Tl])
        return aSave(Tl, result)
    else:
        result = sum([getNumber(v) for v in Tl])
        result = True, aSave(Tl, result)
        if result == 21:
            return result
        result = sum([getNumber(v) for v in (Tl[:-1])])
        return False, aSave(Tl[:-1], result)


# 字符 转 数字
def getNumber(key):
    try:
        return int(key)
    except:
        if key == "A":
            return 11
        return 10


# 整理 列表组
def sortOut():
    startList = startCard()

    # 初始化 计算队列
    T = []
    for v in startList.values():
        x = getSum(v, False)
        T.append({
            "Oknum": x[1],
            "AllOk": x[0],
            "list": v,
            "isEnd": False,
            "show": 2,
            "double": 0
        })

    # 换牌概率
    chance = Config.get_config("TZ21", "CHANCE")
    # 计算 开局换牌
    for v in T:

        l1 = list(v["list"])
        NumberList = [getNumber(x) for x in v["list"]]
        exchange = []
        l1[-1], l1[-2] = l1[-2], l1[-1]
        # 如果 最后一位大于倒数第二位 且 交换之后 炸了
        if getNumber(v["list"][-1]) > getNumber(v["list"][-2]) and getSum(l1, True) > 21:
            exchange.append('v["list"] = l1')

        # 如果 最后一位大于倒数第二位 且 交换之后 正好21
        if getNumber(v["list"][-1]) > getNumber(v["list"][-2]) and getSum(l1, True) == 21:
            exchange.append('v["list"] = l1')

        # 如果 最后一位小于倒数第二位 且 交换之后 且 到倒数第三位结束 和 小于 17
        if getNumber(v["list"][-1]) < getNumber(v["list"][-2]) and getSum(l1[-2:]) < 17:
            exchange.append('v["list"] = l1')

        # 如果最大值不在后两位
        if NumberList.index(max(NumberList)) > len(NumberList) - 1:
            at = NumberList.index(min(NumberList[-2:]))
            maxAt = NumberList.index(max(NumberList))
            exchange.append(
                f'v["list"]["{at}"],v["list"]["{maxAt}"] = v["list"]["{maxAt}"],v["list"]["{at}"]')

        # 判断是否执行换牌
        if len(exchange) > 0 and random.randint(1, 10) <= chance:
            exec(random.choice(exchange))

        # 随机两位调换
        if random.randint(1, 20) <= chance:
            keys = random.choices(range(len(v["list"]) - 1), k=2)
            v["list"][keys[0]], v["list"][keys[1]
            ] = v["list"][keys[1]], v["list"][keys[0]]

    return T


async def upadte_gold():
    global Ginfo
    for gid in Ginfo:
        # 归零
        Ginfo[gid]["gold"] = 0
