from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.permission import GROUP
from configs.config import NICKNAME
from models.bag_user import BagUser
from cn2an import cn2an
from nonebot import on_command
from nonebot.rule import to_me
from ._model import TZtreasury
import random
from models.sign_group_user import SignGroupUser

__zx_plugin_name__ = "乞讨福利金"
__plugin_usage__ = f"""
usage：
    向{NICKNAME}乞讨，有每日次数上限
    指令：
       @{NICKNAME} 行行好给点钱
       @{NICKNAME} 看看小金库
       @{NICKNAME} 捐助金币 num?[num = 1000]
       @{NICKNAME} 充盈金库 num?[num = 1000]
    福利金从金库抽取
""".strip()
__plugin_des__ = f"让{NICKNAME}给你钱，有冷却时间"
__plugin_type__ = ("群内小游戏",)
__plugin_cmd__ = [
    "行行好给点钱", "乞讨福利金"
]
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["行行好给点钱", "乞讨福利金"],
}

__plugin_count_limit__ = {
    "max_count": 5,
    "status": True,
    "rst": f"[at]{NICKNAME}今天不会再给你钱了！"
}

charity = on_command("行行好给点钱", priority=5, rule=to_me(),
                     permission=GROUP, block=True)


@charity.handle()
async def _(event: GroupMessageEvent):
    uid = event.user_id
    group = event.group_id

    # 获取基础数据
    golds = await TZtreasury.get_group_treasury(group_id=group)
    if golds < 10:
        await charity.finish(f"{NICKNAME}的金库里也没钱了\n快去交税吧")

    user_qq_list, impression_list, user_group = await SignGroupUser.get_all_impression(group_id=group)

    # 好感度在当前群占比
    try:
        parent = impression_list[user_qq_list.index(uid)] / sum(impression_list)
    except ValueError as e:
        await charity.finish(f"先去签到再来找{NICKNAME}要钱吧")  # 报错请先签到试试
    except ZeroDivisionError as e:
        await charity.finish(f"你和{NICKNAME}甚至都不认识（你的好感度咋是零捏？）")  # 好感度为零及时结束，防止parent下传导致出现其他无关又看不懂的报错
    maxNum = golds * 0.9 * parent * random.randint(4, 8) / 10
    minNum = maxNum * 0.5 * parent * random.randint(2, 6) / 10
    if minNum > maxNum:
        minNum, maxNum = maxNum, minNum

    gold = random.randint(int(minNum), int(maxNum))
    await BagUser.add_gold(uid, group, gold)
    await TZtreasury.update_treasury_info(group, -gold)

    await charity.finish(
        random.choice(
            [
                f"你捡到了{NICKNAME}遗失的贵重物，{NICKNAME}为了表达感谢从金库里拿出 {gold} 枚金币给你",
                f"{NICKNAME}向你丢出一袋金币，你打开一看，发现里面有" + str(gold) + "枚金币",
                f"大笨蛋你在里面吗？拿着，这是{NICKNAME}赏你的" + str(gold) + "枚金币",
                "用这" + str(gold) + "枚金币去买你想买的东西吧（误"
            ]
        )
    )


gold = on_command("看看小金库", priority=5, rule=to_me(), permission=GROUP, block=True)


@gold.handle()
async def _(event: GroupMessageEvent):
    my = await TZtreasury.get_or_none(group_id=event.group_id)
    if my:
        await gold.finish(f"{NICKNAME}的金库中存有{my.money}枚金币")


upa = on_command("捐助金币", priority=5, rule=to_me(), permission=GROUP, block=True)


@upa.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    num = 1000
    uid = event.user_id
    group = event.group_id

    if arg.extract_plain_text().strip() != "":
        try:
            num = int(cn2an(arg.extract_plain_text().strip(), mode="smart"))
        except ValueError:
            num = 1000
    if 500 > num:
        await upa.finish("少于500金币就不要捐了吧")
        return

    user = await BagUser.get_gold(uid, group)
    if user < num:
        await upa.finish("你并没有这些钱")
        return

    await BagUser.spend_gold(uid, group, num)
    await TZtreasury.update_treasury_info(group_id=event.group_id, num=num)

    await gold.finish(f"你成功的向{NICKNAME}的金库捐赠了{num}枚金币")


addTZtreasury = on_command(
    "充盈金库", rule=to_me(), priority=1, permission=SUPERUSER, block=True
)


@addTZtreasury.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    num = 1000
    if arg.extract_plain_text().strip() != "":
        try:
            num = int(cn2an(arg.extract_plain_text().strip(), mode="smart"))
        except ValueError:
            num = 1000
    await TZtreasury.update_treasury_info(group_id=event.group_id, num=num)

    await gold.finish(f"你成功的向{NICKNAME}的金库填充了{num}枚金币")
