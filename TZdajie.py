from re import T, X
from nonebot import on_command, Driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from utils.utils import get_message_text, get_message_at
from models.group_member_info import GroupInfoUser
from utils.image_utils import text2image
from utils.message_builder import image
from models.ban_user import BanUser
from models.bag_user import BagUser
from models.TZtreasury import TZtreasury
from basic_plugins.ban.data_source import a_ban
from basic_plugins.shop.shop_handle.data_source import register_goods
import nonebot
import random
import time

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

__zx_plugin_name__ = "打劫"
__plugin_usage__ = """
usage：
    一个不要脸的打劫功能。劫富济贫，快试试吧！
    打劫的金额为低的一方金额内随机值
    指令：
    #打劫 [@user]
    #负数修正
        当你的金币数量为负数的时候可以纠正过来
        不过会少很多钱
""".strip()
__plugin_des__ = "打劫!"
__plugin_cmd__ = ["打劫"]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["打劫 [@user]"],
}

__plugin_cd_limit__ = {
    "cd": 120,
    "limit_type": "user",
    "rst": None,
}


save = {}
savetime = 1800
enableCD = True

if enableCD:
    driver: Driver = nonebot.get_driver()

    @driver.on_startup
    async def _():
        await register_goods(
            "菜刀", 500, "进可攻退可守（影响抢劫概率，自动使用）"
        )

dj = on_command("#打劫",  priority=5, block=True)


@dj.handle()
async def _(event: GroupMessageEvent):
    qq = get_message_at(event.json())
    qq = qq[0]
    uid = event.user_id
    group = event.group_id

    if qq == uid:
        await dj.finish("你要干啥？自己打劫自己？", at_sender=True)
        return

    if uid in save.keys():
        save[uid] = 0

    if qq in save.keys() and save[qq] > time.time():
        await dj.finish(f"""对方刚被打劫过，被警方层层保护，不好下手。\n要不等{'%.2f' % (int(save[qq]-time.time())/60+0.5)}分后回来看看？""", at_sender=True)
        return

    name = await GroupInfoUser.get_member_info(qq   , group)
    if name == None:
        await dj.finish("你找不到打劫的对象，不如叫他先去签到？", at_sender=True)
        return

    xgold1 = await BagUser.get_gold(qq, group)
    xgold2 = await BagUser.get_gold(uid, group)

    #没钱不能打劫
    if xgold1 < 10:
        await dj.finish("这人都可以上街乞讨去了，你真的忍心下手吗？", at_sender=True)

    # 获取菜刀
    if enableCD:
        d1 = await BagUser.get_property(qq, group)
        d2 = await BagUser.get_property(uid, group)
        if "菜刀" in d1:
            d1 = d1["菜刀"]
            await BagUser.delete_property(qq, group, "菜刀")
        else:
            d1 = 0
        if "菜刀" in d2:
            d2 = d2["菜刀"]
            await BagUser.delete_property(uid, group, "菜刀")
        else:
            d2 = 0

    text = ""
    #双方菜刀 大概率对砍
    if random.randint(0, 100) > 100 and d1 and d2:
        f = random.randint(10, 30)
        t = random.randint(1, 7)
        text += "\n双方都持有菜刀\n"
        if t > 3:
            f += int(t**2/2)
            text += f"斗争更激烈,掉落量增加{int(t**2/2)}%\n"
        elif t == 3:
            text += f"斗争僵持不下，掉落率没有变化\n"
        else:
            f -= int(t**3/2)
            text += f"{name.user_name}更好的保护住了自己的财产，掉落率降低{int(t**3/2)}%\n"

        cost = int(f * xgold1 /100)
        text += f"总掉落量{f}%({ cost })"
        await BagUser.spend_gold(qq, group, cost)
        await BagUser.add_gold(uid, group, cost)
        await dj.finish(text, at_sender=True)
        return
    
    check = random.randint(1, 121)
    if enableCD:
        #d1 被打劫的
        if d1:
            check -= random.randint(5, 9)
        if d2:
            check += random.randint(3, 12)
    cost = (min(xgold1,xgold2)*0.75 + max(xgold1,xgold2)*0.75)*0.75
    if cost > xgold1:
        cost = xgold1 * 0.5
    cost = int(cost + 10)
    

    if check >120:
        cost = int(0.5 * xgold1)
        await BagUser.spend_gold(qq, group, cost)
        text = f'\n你把{name.user_name}五花大绑，并在{name.user_name}身上翻出{str(cost)}（50%）枚金币!!!\n'
        await BagUser.add_gold(uid, group, cost)
        save[qq] = int(time.time() + savetime)
    elif check >= 55:
        isMax = False
        if cost > xgold1:
            isMax = True
            cost = xgold1

        if check >= random.randint(75,90):
            text = f'\n你一蹦而出，大喊打劫！\n{name.user_name}屈服于你淫威之下，拱手奉上{str(cost)}枚金币!!!'
            if enableCD:
                if d2 and isMax == False:
                    text += f'\n你晃动着菜刀，淡淡的问道就这？\n{name.user_name}又拱手奉上{str(int(cost/10))}枚金币!!!\n'
                    cost += int(cost/10)
                elif d2:
                    text += f'\n你晃动着菜刀，淡淡的问道就这？\n不过你从{name.user_name}身上一毛都没翻出来\n'
            save[qq] = int(time.time() + savetime)
            await BagUser.spend_gold(qq, group, cost)
            await BagUser.add_gold(uid, group, cost)
        else:
            num = int((100-check)/100 * cost)
            text = f'\n你一蹦而出，大喊打劫！\n{name.user_name}屈服于你淫威之下，拱手奉上{str(cost)}枚金币!!!\n不过逃跑时过于紧张丢掉了其中的{100-check}%({num}金币)\n其中60%（{int(0.6*num)}）已收集到小金库\n'
            if enableCD:
                if d2:
                    f = random.randint(15,35)
                    text += f'不过你又提着刀找回丢失的{f}%（{int(num*f/100)}）\n核算下来也就丢失了{num}'
                    num -= int(num*f/100)
            save[qq] = int(time.time() + savetime)
            await TZtreasury.add( group, int(0.6*num))
            await BagUser.spend_gold(qq, group, cost)
            await BagUser.add_gold(uid, group, (cost - num))
    else:
        if check < random.randint(15,20):
            l = random.randint(5,15)
            m = int((check+l )*xgold2/100)
            text = f'\n警察正好路过把你带去做笔录，你为脱身缴纳了{check+l }%最大金额的罚款（{ m }）\n其中90%（{int(0.9*m)}）已纳入小金库'
            if enableCD:
                if d2:
                    l = random.randint(15,25)
                    m += int(l*xgold2/100)
                    text += f'\n警察看见你所携带的菜刀，额外加手{l}%最大金额的罚款（{ int(l*xgold2/100) }）\n其中90%（{int(0.9*int(l*xgold2/100))}）已纳入小金库'
            await TZtreasury.add( group, int(0.9*m) )
            await BagUser.spend_gold(uid, group, m )

        else:
            cost = int(cost/random.randint(2,4))
            if xgold2 > cost*3:
                text = f'\n{name.user_name}一巴掌把你拍倒在地，你打劫失败，鼻青脸肿的奉上{str(cost)}枚金币...\n'
                
                if enableCD:
                    if d1:
                        cost2 = int(cost/random.randint(5,8))
                        text += f'\n{name.user_name}又把刀架在你脖子上，你又交出了{cost2}金币'
                        cost += cost2
                    await BagUser.add_gold(qq, group, cost)
                    await BagUser.spend_gold(uid, group, cost)

                    if random.randint(0,15) < 5:
                        cost = int(cost / random.randint(4,10)) + 2 
                        gold = await TZtreasury.get( group )

                        if gold > 1000:
                            while cost > gold:
                                cost = int(cost / random.randint(4,10)) + 2
                            
                            text += f"\n你在回家路上又捡到了一点（{ cost }）金币\n"
                            await TZtreasury.spend( group, cost )
                            await BagUser.add_gold(uid, group, cost)

            else:
                text = f"{name.user_name}看你太穷就没收你的金币，不过给你送监狱去了\n\n"
                #text += await a_ban(uid,3600,event.user_name,"你")
                if await BanUser.ban(uid, 4, 1800):
                    text += "你将在这里被关30分钟"
            
    #await dj.finish(text, at_sender=True)
    await dj.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()), at_sender=True)


xz = on_command("#负数修正",  priority=5, block=True)
@xz.handle()
async def _(event: GroupMessageEvent):
    uid = event.user_id
    group = event.group_id
    xgold2 = await BagUser.get_gold(uid, group)
    if xgold2<0:
        await BagUser.add_gold(uid, group,abs(xgold2*1.25))
    else:
        xz.finish("你修复个锤子。你余额又不是负数")
        
