from nonebot import on_command, Driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from models.bag_user import BagUser
from utils.utils import get_message_at, is_number
from models.group_member_info import GroupInfoUser
from utils.image_utils import text2image
from utils.message_builder import image
from models.ban_user import BanUser
from ._model import TZtreasury, TZBlack
from configs.config import Config
from basic_plugins.shop.shop_handle.data_source import register_goods
import nonebot
import random
import time

__zx_plugin_name__ = "打劫"
__plugin_usage__ = """
usage：
    一个不要脸的打劫功能。劫富济贫，快试试吧！
    打劫的金额为低的一方金额内随机值
    打劫后的钱会变成赃款，洗白后才能到手
    指令：
    #劫财 [@user]
    #劫色 [@user]
    #负数修正
        当你的金币数量为负数的时候可以纠正过来
        不过会少很多钱
""".strip()
__plugin_des__ = "打劫!"
__plugin_cmd__ = ["劫财||劫色"]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 1.1
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["劫财 [@user]", "劫色 [@user]"]

}

__plugin_cd_limit__ = {
    "cd": 120,
    "limit_type": "user",
    "rst": "一直打劫是要被盯上的！120秒后再试试吧",
}

__plugin_imprisonment__ = {
    "cd": 300,
    "limit_type": "user",
    "rst": "刚劫完一个又想来一个？你是想当后宫王呢？"
}

Config.add_plugin_config(
    "TZdajie",
    "BAN_TIME",
    3,
    help_="打劫失败进入小黑屋的时长，默认为3小时",
)

Config.add_plugin_config(
    "TZdajie",
    "SAVE_TIME",
    1800,
    help_="被打劫成功保护时长，默认为半小时"
)
save = {}
duration = {}
durationtime = 60

driver: Driver = nonebot.get_driver()


@driver.on_startup
async def _():
    await register_goods(
        "菜刀", 500, "进可攻退可守（影响抢劫掉落率和成功率，自动使用）", daily_limit=2
    )
    await register_goods(
        "电击枪", 500, "防守使用（被抢劫成功概率降为20%，自动使用）", daily_limit=2
    )


jc = on_command("#劫财", aliases={"#打劫"}, priority=5, block=True)


@jc.handle()
async def _(event: GroupMessageEvent):
    qq = get_message_at(event.json())[0]
    uid = event.user_id
    group = event.group_id

    if qq == uid:
        await jc.finish("你要干啥？自己打劫自己？", at_sender=True)

    if uid in save.keys():
        save[uid] = 0

    if qq in save.keys() and save[qq] > time.time():
        await jc.finish(f"""对方刚被打劫过，被警方层层保护，不好下手。\n要不等{'%.2f' % (int(save[qq] - time.time()) / 60 + 0.5)}分后回来看看？""",
                        at_sender=True)

    # 在被别人劫色的监禁cd中
    if qq in duration.keys() and duration[qq] > time.time():
        await js.finish(
            f"""对方在别人手里，被别人保护的很好，不好下手。\n要不等{'%.2f' % (int(duration[qq] - time.time()) / 60 + 0.5)}分后回来看看？""",
            at_sender=True)

    # 获取 被打劫用户名
    q = await GroupInfoUser.get_or_none(user_id=qq, group_id=group)
    if q == None:
        await jc.finish("你找不到打劫的对象，不如叫他先去签到？", at_sender=True)
    else:
        name = q.user_name
    xgold1 = await BagUser.get_gold(qq, group)  # 被打劫者 所有的钱
    xgold2 = await BagUser.get_gold(uid, group)  # 打劫者 所有的钱
    savetime = Config.get_config("TZdajie", "SAVE_TIME")  # 保护时长

    # 没钱不能劫财
    if xgold1 < 10:
        await jc.finish("这人都可以上街乞讨去了，你真的忍心下手吗？", at_sender=True)

    # 获取菜刀
    # d1为被打劫的
    d1 = await BagUser.delete_property(qq, group, "菜刀")
    d2 = await BagUser.delete_property(uid, group, "菜刀")

    # 初始 成功 概率
    succes = 55
    # d1拥有电击枪 被抢劫各部分成功概率下降至20%以下
    text = ""

    # 有电击枪 降低
    if await BagUser.delete_property(qq, group, "电击枪"):
        succes = 96
        text += f"这小伙子有家伙！)成功率下降"

    succes1 = succes * 218 // 100

    # 双方菜刀 大概率对砍
    if random.randint(0, 120) > 60 and d1 and d2:
        f = random.randint(10, 30)
        t = random.randint(1, 7)
        text += "\n双方都持有菜刀\n"
        if t > 3:
            f += int(t ** 2 / 2)
            text += f"斗争更激烈,掉落量增加{int(t ** 2 / 2)}%\n"
        elif t == 3:
            text += f"斗争僵持不下，掉落率没有变化\n"
        else:
            f -= int(t ** 3 / 2)
            text += f"{name}更好的保护住了自己的财产，掉落率降低{int(t ** 3 / 2)}%\n"

        cost = int(f * xgold1 / 100)
        text += f"总掉落量{f}%({cost})"

        # 新增 黑钱逻辑
        myBlock = await TZBlack.get_my_today_all_isBlock(uid=uid, gid=group)
        canAddBlock = 1000 - myBlock

        # 判断 黑钱数量
        if (canAddBlock < cost):
            text += f"\n警察追回{cost - canAddBlock}还给了受害者"
            cost = canAddBlock

        # 先把钱扣了
        await BagUser.spend_gold(qq, group, cost)

        # 对这笔黑钱进行记录
        await TZBlack.add_blackMoney(uid=uid, from_qq=qq, num=cost, gid=group)

        await jc.finish(text, at_sender=True)

    check = random.randint(1, 121)

    # 菜刀 轻度影响概率
    if d1:  # 打劫 成功率 Down 
        check -= random.randint(5, 9)
    if d2:  # 打劫 成功率 UP
        check += random.randint(3, 12)

    # 计算 打劫 金额
    cost = (min(xgold1, xgold2) * 0.75 + max(xgold1, xgold2) * 0.75) * 0.75

    if cost > xgold1:
        cost = xgold1 * 0.5
    cost = int(cost + 10)

    if check > succes1:
        cost = int(0.5 * xgold1)
        text = f'\n你把{name}五花大绑，并在{name}身上翻出{str(cost)}（50%）枚金币!!!\n'

        # 新增 黑钱逻辑
        myBlock = await TZBlack.get_my_today_all_isBlock(uid=uid, gid=group)
        canAddBlock = 1000 - myBlock

        # 判断 黑钱数量
        if (canAddBlock < cost):
            text += f"\n警察追回{cost - canAddBlock}还给了受害者"
            cost = canAddBlock

        # 先把钱扣了
        await BagUser.spend_gold(qq, group, cost)

        # 对这笔黑钱进行记录
        await TZBlack.add_blackMoney(uid=uid, from_qq=qq, num=cost, gid=group)

        save[qq] = int(time.time() + savetime)

    elif check >= succes:
        isMax = False
        if cost > xgold1:
            isMax = True
            cost = xgold1

        if check >= random.randint(succes * 136 // 100, succes * 164 // 100):
            text = f'\n你一蹦而出，大喊打劫！\n{name}屈服于你淫威之下，拱手奉上{str(cost)}枚金币!!!'
            if d2 and isMax == False:
                # 有刀 
                text += f'\n你晃动着菜刀，淡淡的问道就这？\n{name}又拱手奉上{str(int(cost / 10))}枚金币!!!\n'
                cost += int(cost / 10)
            elif d2:
                # 被打劫者 就只有那点钱
                text += f'\n你晃动着菜刀，淡淡的问道就这？\n不过你从{name}身上一毛都没翻出来\n'

            save[qq] = int(time.time() + savetime)

            # 新增 黑钱逻辑
            myBlock = await TZBlack.get_my_today_all_isBlock(uid=uid, gid=group)
            canAddBlock = 1000 - myBlock

            # 判断 黑钱数量
            if (canAddBlock < cost):
                text += f"\n警察追回{cost - canAddBlock}还给了受害者"
                cost = canAddBlock

            # 先把钱扣了
            await BagUser.spend_gold(qq, group, cost)

            # 对这笔黑钱进行记录
            await TZBlack.add_blackMoney(uid=uid, from_qq=qq, num=cost, gid=group)

        else:
            num = abs(int((100 - check) / 100 * cost))
            text = f'\n你一蹦而出，大喊打劫！\n{name}屈服于你淫威之下，拱手奉上{str(cost)}枚金币!!!\n不过逃跑时过于紧张丢掉了其中的{abs(100 - check)}%({num}金币)\n其中60%（{int(0.6 * num)}）已收集到小金库\n'
            if d2:
                f = random.randint(15, 35)
                text += f'不过你又提着刀找回丢失的{f}%（{int(num * f / 100)}）\n核算下来也就丢失了{num}'
                num -= int(num * f / 100)
            save[qq] = int(time.time() + savetime)

            await TZtreasury.update_treasury_info(group, int(0.6 * num))

            # 新增 黑钱逻辑
            myBlock = await TZBlack.get_my_today_all_isBlock(uid=uid, gid=group)
            canAddBlock = 1000 - myBlock

            # 判断 黑钱数量
            if (canAddBlock < cost):
                text += f"\n警察追回{cost - canAddBlock}还给了受害者"
                cost = canAddBlock

            # 先把钱扣了
            await BagUser.spend_gold(qq, group, cost)

            # 对这笔黑钱进行记录
            await TZBlack.add_blackMoney(uid=uid, from_qq=qq, num=cost, inNum=(cost - num), gid=group)

    else:
        if check < random.randint(succes * 27 // 100, succes * 36 // 100):
            l = random.randint(5, 15)
            m = int((check + l) * xgold2 / 100)
            text = f'\n警察正好路过把你带去做笔录，你为脱身缴纳了{check + l}%最大金额的罚款（{m}）\n其中90%（{int(0.9 * m)}）已纳入小金库'
            if d2:
                l = random.randint(15, 25)
                m += int(l * xgold2 / 100)
                text += f'\n警察看见你所携带的菜刀，额外加手{l}%最大金额的罚款（{int(l * xgold2 / 100)}）\n其中90%（{int(0.9 * int(l * xgold2 / 100))}）已纳入小金库'
            await TZtreasury.update_treasury_info(group, int(0.9 * m))
            await BagUser.spend_gold(uid, group, m)

        else:
            cost = int(cost / random.randint(2, 4))
            if xgold2 > cost * 3:
                text = f'\n{name}一巴掌把你拍倒在地，你打劫失败，鼻青脸肿的奉上{str(cost)}枚金币...\n'

                if d1:
                    cost2 = int(cost / random.randint(5, 8))
                    text += f'\n{name}又把刀架在你脖子上，你又交出了{cost2}金币'
                    cost += cost2
                await BagUser.add_gold(qq, group, cost)
                await BagUser.spend_gold(uid, group, cost)

                if random.randint(0, 15) < 5:
                    cost = int(cost / random.randint(4, 10)) + 2
                    gold = await TZtreasury.get_group_treasury(group)

                    if gold > 1000:
                        while cost > gold:
                            cost = int(cost / random.randint(4, 10)) + 2

                        text += f"\n你在回家路上又捡到了一点（{cost}）金币\n"
                        await TZtreasury.update_treasury_info(group, -cost)
                        await BagUser.add_gold(uid, group, cost)

            else:
                text = f"{name}看你太穷就没收你的金币，不过给你送监狱去了\n\n"
                ban_tiem = Config.get_config("TZdajie", "BAN_TIME")
                if not is_number(ban_tiem):
                    ban_tiem = 3
                if int(ban_tiem) <= 0:
                    ban_tiem = 3
                if await BanUser.ban(uid, 4, ban_tiem * 3600):
                    text += f"你将在这里被关{ban_tiem}小时"

    # await jc.finish(text, at_sender=True)
    await jc.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()), at_sender=True)


js = on_command("#劫色", priority=5, block=True)


@js.handle()
async def _(event: GroupMessageEvent):
    qq = get_message_at(event.json())
    qq = qq[0]
    uid = event.user_id
    group = event.group_id

    if qq == uid:
        await js.finish("连自己都不放过？", at_sender=True)
        return

    if uid in save.keys():
        save[uid] = 0

    if qq in save.keys() and save[qq] > time.time():
        await js.finish(f"""对方刚被打劫过，被警方层层保护，不好下手。\n要不等{'%.2f' % (int(save[qq] - time.time()) / 60 + 0.5)}分后回来看看？""",
                        at_sender=True)
        return
    # 在被别人劫色的监禁cd中
    if qq in duration.keys() and duration[qq] > time.time():
        await js.finish(
            f"""对方在别人手里，被别人保护的很好，不好下手。\n要不等{'%.2f' % (int(duration[qq] - time.time()) / 60 + 0.5)}分后回来看看？""",
            at_sender=True)
        return

    q = await GroupInfoUser.get_or_none(user_id=qq, group_id=group)
    if q == None:
        await jc.finish("你找不到打劫的对象，不如叫他先去签到？", at_sender=True)
    else:
        name = q.user_name

    xgold1 = await BagUser.get_gold(qq, group)
    xgold2 = await BagUser.get_gold(uid, group)

    # 有钱不能劫色
    if xgold1 > 10 and xgold2 > xgold1:
        await js.finish("这人手里有点东西，不会屈于你的淫威", at_sender=True)

    # 获取d1是否有电击枪
    d1 = await BagUser.delete_property(qq, group, "电击枪")
    text = ""

    check = random.randint(1, 101)
    succes = 50
    # d1拥有电击枪 被抢劫成功概率下降至20%以下
    if d1:
        succes = 80
        text += f"这小伙子有家伙！)成功率下降"
        # await js.finish(text, at_sender=True)

    # 检测d1和d2是否有菜刀，并影响成功率
    d1 = await BagUser.delete_property(qq, group, "菜刀")
    d2 = await BagUser.delete_property(uid, group, "菜刀")

    if d1:
        check -= random.randint(5, 9)
    if d2:
        check += random.randint(3, 12)

    cost = (min(xgold1, xgold2) * 0.75 + max(xgold1, xgold2) * 0.75) * 0.75
    if cost > xgold1:
        cost = xgold1 * 0.5
    cost = int(cost + 10)

    if check >= succes:
        text = f'\n你把{name}五花大绑，并把{name}丢在了自己的地下室!!!，你将在这经历调教!\n'
        if await BanUser.ban(uid, 4, 60):
            text += f"你将在这里被关1分钟"
        duration[qq] = int(time.time() + durationtime)
    else:
        if check < random.randint(15, 20):
            l = random.randint(5, 15)
            m = int((check + l) * xgold2 / 100)
            text = f'\n警察正好路过把你带去做笔录，你为脱身缴纳了{check + l}%最大金额的罚款（{m}）\n其中90%（{int(0.9 * m)}）已纳入小金库'
            if d2:
                l = random.randint(15, 25)
                m += int(l * xgold2 / 100)
                text += f'\n警察看见你所携带的菜刀，额外加手{l}%最大金额的罚款（{int(l * xgold2 / 100)}）\n其中90%（{int(0.9 * int(l * xgold2 / 100))}）已纳入小金库'
            await TZtreasury.update_treasury_info(group, int(0.9 * m))
            await BagUser.spend_gold(uid, group, m)

        else:
            cost = int(cost / random.randint(2, 4))
            if xgold2 > cost * 3:
                text = f'\n{name}强劲的掌风将你吹倒在地，你被他铮亮的胸毛所震撼，最终鼻青脸肿的奉上{cost}枚金币...\n'

                if d1:
                    cost2 = int(cost / random.randint(5, 8))
                    text += f'\n{name}又把刀架在你脖子上，你为你的行为又交出了{cost2}金币'
                    cost += cost2
                await BagUser.add_gold(qq, group, cost)
                await BagUser.spend_gold(uid, group, cost)

                if random.randint(0, 15) < 5:
                    cost = int(cost / random.randint(4, 10)) + 2
                    gold = await TZtreasury.get_group_treasury(group)

                    if gold > 1000:
                        while cost > gold:
                            cost = int(cost / random.randint(4, 10)) + 2

                        text += f"\n你在回家路上又捡到了一点（{cost}）金币\n"
                        await TZtreasury.update_treasury_info(group, -cost)
                        await BagUser.add_gold(uid, group, cost)

            else:
                text = f"{name}看你太穷就没收你的金币，不过给你送监狱去了\n\n"
                ban_tiem = Config.get_config("TZdajie", "BAN_TIME")
                if not is_number(ban_tiem):
                    ban_tiem = 3
                if int(ban_tiem) <= 0:
                    ban_tiem = 3
                if await BanUser.ban(uid, 4, ban_tiem * 3600):
                    text += f"你将在这里被关{ban_tiem}小时"

    # await js.finish(text, at_sender=True)
    await js.finish(image(b64=(await text2image(text, color="#f9f6f2", padding=10)).pic2bs4()), at_sender=True)


xz = on_command("#负数修正", priority=5, block=True)


@xz.handle()
async def _(event: GroupMessageEvent):
    uid = event.user_id
    group = event.group_id
    xgold2 = await BagUser.get_gold(uid, group)
    if xgold2 < 0:
        await BagUser.add_gold(uid, group, int(abs(xgold2 * 1.25)))
    else:
        await xz.finish("你修复个锤子。你余额又不是负数")
