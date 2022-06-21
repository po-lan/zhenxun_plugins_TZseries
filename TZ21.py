import time
import random
from nonebot import on_command
from models.bag_user import BagUser
from nonebot.params import CommandArg
from utils.message_builder import image
from utils.image_utils import text2image
from nonebot.permission import SUPERUSER
from configs.config import NICKNAME, Config
from nonebot_plugin_apscheduler import scheduler
from models.group_member_info import GroupInfoUser
from utils.utils import get_message_text, is_number, UserBlockLimiter
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent, Message, MessageSegment


async def dl():
    await AsyncHttpx.download_file(
        "https://raw.githubusercontent.com/po-lan/zhenxun_plugins_TZseries/main/models/TZtreasuryV1.py",
        path = path
    )

try:
    from models.TZtreasury import TZtreasury
except:
    from utils.http_utils import AsyncHttpx
    from pathlib import Path
    path = Path("models")  / "TZtreasury.py"
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dl())
    from models.TZtreasury import TZtreasury


__zx_plugin_name__ = "21点"
__plugin_usage__ = f"""
usage：
    第一位玩家发起活动，指令21点[赌注]
    接受21点赌局，指令：入场[赌注]（此指令无反馈）
    人齐后开局，指令：开局
    拿牌指令：拿牌
    宣布停止，指令：停牌（此指令无反馈）
    所有人停牌，或者超时90s后，结算指令：结束
    {NICKNAME} 必要点数17
    起手2牌合计21点为黑杰克，比其他21点大
    获胜奖励为胜者按各自入场费
    如果{NICKNAME}没钱了，就不会再玩了
    当然你可以输入 [21点打钱 金额] 给机器人打钱
""".strip()
__plugin_des__ = f"{NICKNAME}小赌场-21点"
__plugin_cmd__ = ["21点 [赌注]/继续/结算"]
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
        "name":"流水控制",
        "help": "通过算牌等 使群内不会使用21点刷钱过快",
        "default_value": True
    },
    "CHANCE": {
        "value": 3,
        "help": "0-10;0为关",
        "name":"开局前随机换牌概率",
        "default_value": 3
    }
}


Ginfo = {}
blk = UserBlockLimiter()

#定时刷新
async def update():
    for gid in Ginfo:
        gold = Ginfo[gid]["gold"]
        if gold > 0:
            try:
                from .TZggl import TZlottery
                gold += await TZlottery.getLotteryGold(gid)
                await TZlottery.setLotteryGold(gid,gold)
            except:
                pass
        #归零
        Ginfo[gid]["gold"] = 0

scheduler.add_job(
    update,
    "cron",
    hour="*/2",
    id="TZ21_gold_0",
)

dq = on_command("21点打钱", priority=5, block=True)
@dq.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
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


opendian = on_command("21点", priority=5, block=True)
@opendian.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    gid = event.group_id
    uid = event.user_id
    if blk.check(gid):
        await opendian.finish()
    blk.set_true(gid)


    # 获取用户名
    uname = event.sender.card if event.sender.card else event.sender.nickname
    # 判断上一场是否结束
    if gid in Ginfo:
        #有这个群的数据
        if Ginfo[gid]["state"] != 0:
            blk.set_false(gid)
        if Ginfo[gid]["state"] == 1:
            #state : 已开场，未开局
            await opendian.finish(f"上一场21点还未开始，请输入入场\n")
        if Ginfo[gid]["state"] == 2:
            #state : 已开局，未结束
            await opendian.finish(f"上一场21点还未结束，请等待\n")

    # 判断入场赌注
    msg = arg.extract_plain_text().strip()
    if msg:
        if is_number(msg) and int(msg) > 0:
            cost = int(msg)
            if cost > 10000:
                blk.set_false(gid)
                await opendian.finish(f"{NICKNAME}不接受10000以上的赌注哦", at_sender=True)
            if cost < 20:
                blk.set_false(gid)
                await opendian.finish(f"{NICKNAME}觉得20以下的赌注不得劲哎", at_sender=True)
        else:
            blk.set_false(gid)
            await opendian.finish(f"赌注是数字啊喂", at_sender=True)
    else:
        blk.set_false(gid)
        await opendian.finish(f"请输入你的赌注", at_sender=True)
    
    # 输多了 就摆烂
    if gid in Ginfo and -14514 > Ginfo[gid]["gold"]:
        await opendian.finish(f"{NICKNAME}输的有点多了，{NICKNAME}去打工赚钱陪你们玩")

    # 判断 是否够用
    if await BagUser.get_gold(uid, gid) < cost:
        blk.set_false(gid)
        await opendian.finish(f"\n金币不够还想来21点？\n您的金币余额为{str(await BagUser.get_gold(uid, gid))}", at_sender=True)

    if gid not in Ginfo:
        Ginfo[gid] = {"gold": 0, "state": 1}

    Ginfo[gid]["players"] = {}
    Ginfo[gid]["state"] = 1
    Ginfo[gid]["initCost"] = cost
    Ginfo[gid]["startUid"] = uid
    Ginfo[gid]["freeCard"] = []
    Ginfo[gid]["time"] = time.time()

    await ruchangx(gid, uid, uname, cost)
    blk.set_false(gid)
    await opendian.finish(f'{uname}发起了一场21点挑战')


ruchang = on_command("入场", priority=5, block=True)
@ruchang.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    gid = event.group_id
    uid = event.user_id
    #阻断 防止触发过快
    if blk.check(gid):
        await ruchang.finish()
    blk.set_true(gid)
    
    # 判断上一场是否结束
    if gid in Ginfo:
        #有这个群的数据
        if Ginfo[gid]["state"] == 0:
            #state : 未开场
            blk.set_false(gid)
            await opendian.finish(f"请先开场、开场后会自动入场")
        if Ginfo[gid]["state"] == 2:
            #state : 已开局，未结束
            blk.set_false(gid)
            await opendian.finish(f"上一场21点还未结束，请等待")
    else:
        #没有本群数据
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
    if cost < (Ginfo[gid]["initCost"] / 2):
        blk.set_false(gid)
        await ruchang.finish(f"赌注不得小于开局玩家的1/2", at_sender=True)

    uname = event.sender.card if event.sender.card else event.sender.nickname
    blk.set_false(gid)
    await ruchangx(gid, uid, uname, cost)

# 入场 记录
async def ruchangx(gid: int, uid: int, uname: str,  cost: int):

    Ginfo[gid]["players"][uid] = {
        "uname": uname,
        "cost": cost,
        "BJ": False,
        "uid": uid
    }
    Ginfo[gid]["time"] = time.time()
    await BagUser.spend_gold(uid, gid, cost)


# 开局
kaiju = on_command("开局", priority=5, block=True)
@kaiju.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    gid = event.group_id
    uid = event.user_id
    # 判断上一场是否结束
    if gid in Ginfo:
        #有这个群的数据
        if Ginfo[gid]["state"] == 0:
            #state : 未开场
            await opendian.finish(f"请先开场、开场后等待他人入场结束后在输入")
        if Ginfo[gid]["state"] == 2:
            #state : 已开局，未结束
            await opendian.finish(f"上一场21点还未结束，请等待")
    else:
        #没有本群数据
        await opendian.finish(f"请先开场、开场后等待他人入场结束后在输入")

    # 判断是不是开场的人发的开局
    if Ginfo[gid]["startUid"] != uid:
        await opendian.finish(f"开场的人开局，别人别瞎搅合\n")

    # 停止入场
    Ginfo[gid]["state"] = 2

    # 生成牌组，且当牌组为7时重新生成
    Card = sortOut()
    while len(Card) == 7:
        Card = sortOut()

    # 机器人加入游戏
    Gcost = sum([v["cost"] for v in Ginfo[gid]["players"].values()]
                ) / (len(Ginfo[gid]["players"]))
    Ginfo[gid]["players"][0] = {
        "uid": 0,
        "BJ": False,
        "uname": NICKNAME,
        "cost": int(0)
    }

    # 基于牌组 分配
    if False:
        # 出千模式
        # 
        # 还没想好怎么出千
        pass
    else:
        # 正常模式
        for i, key in enumerate(Ginfo[gid]["players"]):
            Ginfo[gid]["players"][key] = {
                **Card[i], **Ginfo[gid]["players"][key]}
        
    #回收空牌
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
        text += f"{v['uname']} 的牌为：{','.join(v['list'][:v['show']])}"
        if v["BJ"]:
            text += " 已BlackJack，"

        text += f"总点数为：{getSum(v['list'][:v['show']])}\n"

    await opendian.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()))


napai = on_command("拿牌", priority=5, block=True)
@napai.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    uid = event.user_id
    gid = event.group_id
    #阻断 防止过快
    if blk.check(gid):
        await napai.finish()
    blk.set_true(gid)
    # 判断上一场是否结束
    if gid in Ginfo:
        #有这个群的数据
        if Ginfo[gid]["state"] == 0:
            #state : 未开场
            blk.set_false(gid)
            await opendian.finish(f"请先开场、开局后才能拿牌")
        if Ginfo[gid]["state"] == 1:
            #state : 已开局，未结束
            blk.set_false(gid)
            await opendian.finish(f"请先开局、开局后才能拿牌")
    else:
        #没有本群数据
        blk.set_false(gid)
        await opendian.finish(f"请先开场、开局后才能拿牌")
    
    #如果玩家不在列表里
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


tingpai = on_command("停牌", priority=5, block=True)
@tingpai.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    uid = event.user_id
    gid = event.group_id
    # 判断 是否已经开局

    if gid in Ginfo:
        if Ginfo[gid]["state"] != 2:
            await tingpai.finish("还没开局呢，停个锤子")
    else:
        await tingpai.finish("你都没开场过，停个锤子")

    #如果玩家不在列表里
    if uid not in Ginfo[gid]["players"]:
        await opendian.finish(f"无关人员不要捣乱\n")

    Ginfo[gid]["players"][uid]["isEnd"] = True


jiesuan = on_command("结束", priority=5, block=True)
@jiesuan.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    uid = event.user_id
    gid = event.group_id
    # 判断 是否已经开局
    if gid in Ginfo:
        if Ginfo[gid]["state"] != 2:
            await jiesuan.finish("还没开局呢，结束个锤子")
    else:
        await jiesuan.finish("你都没开场过，结束个锤子")

    #如果玩家不在列表里
    if uid not in Ginfo[gid]["players"]:
        await opendian.finish(f"无关人员不要捣乱\n")
    
    # 判断是不是开场的人发的开局
    if Ginfo[gid]["startUid"] != uid:
        await opendian.finish(f"开场的人结束，别人别瞎搅合")

    # 判断是否全部玩家都停牌了
    def getEnd(T):
        BackList = []
        #超时后可以直接结束
        if  time.time() - Ginfo[gid]["time"]> 90:
            return [True]
        #判断 玩家是否全部停牌
        for v in T:
            #机器人 和 发起者 都可以当作 已经停牌
            if v["uid"] == 0 or v["uid"] == Ginfo[gid]["startUid"]:
                BackList.append(True)
                break
            BackList.append(v["isEnd"])
        return BackList

    if all(getEnd(Ginfo[gid]["players"].values())) == False:
        await tingpai.finish("还有人没停牌")

    # 计算结果
    await end(gid)


async def end(gid):
    # 让机器人的牌先打到17
    while getSum(Ginfo[gid]["players"][0]["list"][:Ginfo[gid]["players"][0]["show"]]) < 17:
        Ginfo[gid]["players"][0]["show"] += 1

    BotS, BotBoom, text = 0, False, ""

    def isBOOM(T):
        if T["uid"] == 0:
            return False
        return getSum(T["list"][:T["show"]]) > 21

    def isNotBoom(T):
        if T["uid"] == 0:
            return False
        return getSum(T["list"][:T["show"]]) < 22

    def GetWinUser(T):
        if T["uid"] == 0:
            return False
        s = getSum(T["list"][:T["show"]])
        #如果 炸了 直接 跳过
        if s > 21:
            return False
        if BotBoom:
            #如果机器人炸了，所所有没炸的人，都赢
            return True
        else:
            #机器人是黑杰克
            if Ginfo[gid]["players"][0]["BJ"]:
                return False
            else:
                #如果机器人 和玩家 点数相同 ，且 玩家牌比机器人少
                if BotS == s and Ginfo[gid]["players"][0]["show"] > T["show"]:
                    return True
                else:
                    #机器人和玩家点数不相同
                    # 黑杰克 或者 比机器人点数大的赢
                    if T["BJ"] or s > BotS:
                        #玩家中黑杰克赢
                        #点数大于机器人的赢
                        return True
        

    # 先计算炸了的
    for value in list(filter(isBOOM, Ginfo[gid]["players"].values())):
        text += f"{value['uname']}的牌是：{','.join(value['list'][:value['show']])} 炸了\n"

    # 计算 玩家 最大的得分
    ss = [getSum(v['list'][:v['show']]) for v in list(filter(isNotBoom, Ginfo[gid]["players"].values()))]
    ss.append(0)
    UserMax = max(ss)

    gold = 0
    #收集金币0
    for v in list(Ginfo[gid]["players"].values()):
        gold += v["cost"]
    
    if Ginfo[gid]["gold"] < gold / 2 and Config.get_config("TZ21", "FC") and Ginfo[gid]["players"][0]["BJ"] == False:
        #出千 
        check = random.randint(1,3)
        if check == 1:
            l1 = list(Ginfo[gid]["players"][0]["list"])
            l1[-1], l1[-2] = l1[-2], l1[-1]
            # 如果 最后两位交换之后 正好21
            if getSum(l1, True) == 21:
                Ginfo[gid]["players"][0]["list"] = l1
                Ginfo[gid]["players"][0]["show"] = len(l1)
            elif getSum(l1[:-1], True) == 21:
                Ginfo[gid]["players"][0]["list"] = l1[:-1]
                Ginfo[gid]["players"][0]["show"] = len(l1[:-1])

        if check == 2:
            #换底牌，是牌组跟接近21
            T1 = Ginfo[gid]["players"][0]["list"][:2]
            Ginfo[gid]["freeCard"].append(Ginfo[gid]["players"][0]["list"][2:])
            if UserMax != 21 and getSum(T1) > 16:
                x = 21 - getSum(T1)
                isNotOK = True
                while isNotOK and x > 1:
                    if x in Ginfo[gid]["freeCard"]:
                        T1.append(x)
                        Ginfo[gid]["freeCard"].remove(x)
                        isNotOK = False
            
            while getSum(T1) < UserMax:
                x = Ginfo[gid]["freeCard"][0]
                T1.append(x)
                Ginfo[gid]["freeCard"].remove(x)
            
            Ginfo[gid]["players"][0]["list"] = T1
            Ginfo[gid]["players"][0]["show"] = len(T1)

        if getSum(Ginfo[gid]["players"][0]["list"], True) > 21:
            T1 = Ginfo[gid]["players"][0]["list"][:2]
            T2 = []
            i = 0
            Ginfo[gid]["freeCard"].append(Ginfo[gid]["players"][0]["list"][2:])

            def aNew():
                T2 = list(T1) + random.choices(Ginfo[gid]["freeCard"],k=3)
                return 21 < getSum(T2) <= UserMax
            
            while aNew() and i < 200:
                i += 1
                Ginfo[gid]["players"][0]["list"] = T2
                Ginfo[gid]["players"][0]["show"] = len(T2)

    else:
        # 按照玩家的得分 让机器人摸牌
        while UserMax >= getSum(Ginfo[gid]["players"][0]["list"][:Ginfo[gid]["players"][0]["show"]]) < 22:
            Ginfo[gid]["players"][0]["show"] += 1

    #提取没炸的人
    for value in list(filter(isNotBoom, Ginfo[gid]["players"].values())):
        text += f"{value['uname']}的牌是：{','.join(value['list'][:value['show']])}\n"

    # 判断机器人是炸了还是赢了
    BCard = Ginfo[gid]["players"][0]["list"][:Ginfo[gid]["players"][0]["show"]]
    BotS = getSum(BCard)


    if BotS < 22:
        text = f"{NICKNAME}的牌是：{','.join(BCard)},总点数为{BotS}\n" + text
    else:
        text = f"{NICKNAME}的牌是：{','.join(BCard)},总点数为{BotS}，炸了\n" + text
        BotBoom = True
        # 计算玩家胜利
    
    winUsers = list(filter(GetWinUser, Ginfo[gid]["players"].values()))
    if len(winUsers) > 0:
        #胜利的用户
        text += f'\n本场胜利的：'
        for v in winUsers:
            text += f'\n{v["uname"]} 赢得了 {v["cost"]}金币--税{int(v["cost"]*0.2)}'
            await TZtreasury.add(gid,int(v["cost"]*0.2))
            await BagUser.add_gold(v["uid"], gid, int(v["cost"]*1.8))
            gold -= v["cost"]*2
    else:
        #没人胜利
        text += f"{NICKNAME} 收走了全部的金币"

    #  金币 加入累计
    Ginfo[gid]["gold"] += gold
    if gold >= 0:
        text += f"\n{NICKNAME}本局赚了{gold}金币"
    else:
        text += f"\n{NICKNAME}本局赔了{abs(gold)}金币"

    #  await jiesuan.send_msg(message=image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()),group_id=gid)

    # 恢复状态
    Ginfo[gid]["state"] = 0

    await jiesuan.finish(message=image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()), group_id=gid)

#控制部分

#流水控制
FC = on_command("21点流水控制", priority=5, permission=SUPERUSER, block=True)
@FC.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg == "开":
        Config.set_config("TZ21", "FC", True)
        await chance.finish(f"流水控制已开启", at_sender=True)
    elif msg == "关":
        Config.set_config("TZ21", "FC", False)
        await chance.finish(f"流水控制已关闭", at_sender=True)
    else:
        await chance.finish(f"参数只能为开或关", at_sender=True)

        

# 奖池调整
chance = on_command("开局前随机换牌概率", priority=5, permission=SUPERUSER, block=True)
@chance.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if is_number(msg) and int(msg) > -1:
        if int(msg) < 11:
            Config.set_config("TZ21", "CHANCE", int(msg))
            await chance.finish(f"概率已调整为{int(msg)*10}%", at_sender=True)
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
            v["list"][keys[0]], v["list"][keys[1]] = v["list"][keys[1]], v["list"][keys[0]]

    return T