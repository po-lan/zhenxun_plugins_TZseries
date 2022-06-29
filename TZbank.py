from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg
from nonebot import on_command, logger
from nonebot.permission import SUPERUSER
from utils.utils import scheduler
from utils.utils import get_message_at, is_number
from utils.message_builder import image
from utils.data_utils import init_rank
from configs.config import NICKNAME, Config
from ._model import TZtreasury, TZBank
from models.bag_user import BagUser
from models.sign_group_user import SignGroupUser

__zx_plugin_name__ = "银行"
__plugin_usage__ = f"""
usage：
    {NICKNAME}的银行绝对安全，不会被打劫
    不过也有一点手续费
    存入的金额不可高于 自己拥有总额的70%
    指令：
        #银行存入 num
        #银行取出 num
        #银行汇款 [@user] num 
        #个人汇款 [@user] num
          这个会汇入到对方的银行
          不超过手头资产的30%
        #个人转账 [@user] num
          人对人
          不超过手头资产的70%
        #我的存款
        #存款排行 ?num=10
    ?表示可选参数 =为默认值
    福利金从金库抽取
""".strip()
__plugin_des__ = "一个金币暂存处，可以防止打劫"
__plugin_type__ = ("群内小游戏",)
__plugin_cmd__ = [
    "#银行存入",
    "#银行取出",
    "#银行汇款",
    "#个人汇款",
    "#个人转账",
    "#我的存款",
    "#存款排行"
]
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["#银行存入", "#银行取出", "#银行汇款", "#个人汇款", "#个人转账", "#我的存款", "#存款排行"],
}
__plugin_configs__ = {
    "MAX_MONEY_BASICS": {"value": 1000, "help": "银行存款基础上限", "default_value": 1000},
    "MAX_MONEY_MULTIPLIER": {"value": 100, "help": "银行存款金额上限倍率，总上限=基础上限+倍率*好感度", "default_value": 100}}


# 超出百分之70自动转出
# @scheduler.scheduled_job(
#     "interval",
#     seconds=30,
# )
# async def _():
#     await update_bank_70()


save = on_command("#银行存入", priority=5, permission=GROUP, block=True)


@save.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"连一金币都不存你要干啥")
        elif num == 1:
            await save.finish(f"最低手续费要一金币哟，你要给{NICKNAME}送钱嘛")
    except:
        await save.finish("存款额只能是数字")

    uid = event.user_id
    group = event.group_id
    gold = await BagUser.get_gold(uid, group)
    inbank = await TZBank.get(uid, group)
    all = gold + inbank
    # 手续费
    charges = int(num * 0.03) if int(num * 0.03) > 1 else 1
    CanSave = all * 0.7 - inbank
    if CanSave >= num:
        if gold < num:
            await save.finish(f"你的钱好像不够啊")
        max_money = await calculation_max_money(uid, group)
        if inbank + num - charges > max_money:
            CanSave = int((max_money - inbank) * 1.03)
            await save.finish(f"存入失败\n存入超过银行上限\n提高跟{NICKNAME}的好感度能增加上限哦\n还可存入：{int(CanSave) if int(CanSave) > 0 else 0}")
        else:
            await BagUser.spend_gold(uid, group, num)
            await TZtreasury.add(group, charges)
            await TZBank.add(uid, group, num - charges)
            await save.finish(f"{num}成功存入\n{NICKNAME}收取了3%({charges})的手续费")
    else:
        await save.finish(f"存入失败\n存取超过拥有总额的70%\n当前最大可存入{int(CanSave) if int(CanSave) > 0 else 0}")


take = on_command("#银行取出", priority=5, permission=GROUP, block=True)


@take.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await take.finish(f"连一金币都不取你要干啥")
        elif num == 1:
            await take.finish(f"最低手续费要一金币哟，你要给{NICKNAME}送钱吗")
    except:
        await take.finish("取款额只能是数字")

    uid = event.user_id
    group = event.group_id
    inbank = await TZBank.get(uid, group)
    # 手续费
    charges = int(num * 0.07) if int(num * 0.07) > 1 else 1
    if num > inbank:
        await take.finish(f"你的钱好像不够啊")
    else:
        await TZBank.spend(uid, group, num)
        await BagUser.add_gold(uid, group, num - charges)
        await TZtreasury.add(group, charges)
        await take.finish(f"{num}成功取出\n{NICKNAME}收取了7%({charges})的手续费")


bankMove = on_command("#银行汇款", priority=5, permission=GROUP, block=True)


@bankMove.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await bankMove.finish(f"汇款额一金币都不到你要干啥")
        elif num == 1:
            await bankMove.finish(f"最低手续费要一金币哟，你要给{NICKNAME}送钱吗")
    except:
        await bankMove.finish("汇款额只能是数字")

    qq = get_message_at(event.json())
    if len(qq) > 0:
        toqq = qq[0]
    else:
        await bankMove.finish("倒是@你要汇款的人啊")

    uid = event.user_id
    # 防止转账对象是自己
    if toqq == uid:
        await bankMove.finish("你要给自己汇款？你信不信我能把你钱全吞了")

    group = event.group_id
    inbank = await TZBank.get(uid, group)
    # 手续费
    charges = int(num * 0.01) if int(num * 0.01) > 1 else 1
    if num > inbank:
        await bankMove.finish(f"你的钱好像不够啊")
    else:
        gold = await BagUser.get_gold(toqq, group)
        inbank_to = await TZBank.get(toqq, group)
        all = gold + inbank_to
        CanSave = all * 0.7 - inbank_to
        if CanSave >= num:
            max_money = await calculation_max_money(toqq, group)
            if inbank_to + num - charges > max_money:
                CanSave = int((max_money - inbank_to) * 1.01)
                await bankMove.finish(
                    f"转入失败\n转入超过对方银行上限\n提高跟{NICKNAME}的好感度能增加上限哦\n还可转入：{int(CanSave) if int(CanSave) > 0 else 0}")
            else:
                await TZBank.spend(uid, group, num)
                await TZBank.add(toqq, group, num - charges)
                await TZtreasury.add(group, charges)
                await bankMove.finish(f"{num}成功转入对方的银行账户\n{NICKNAME}收取了1%({charges})的手续费")
        else:
            await bankMove.finish(f"转入失败\n转入超过对方拥有总额的70%\n当前最大可转入{int(CanSave) if int(CanSave) > 0 else 0}")


PMove = on_command("#个人汇款", priority=5, permission=GROUP, block=True)


@PMove.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await PMove.finish(f"汇款额一金币都不到你要干啥")
        elif num == 1:
            await PMove.finish(f"最低手续费要一金币哟，你要给{NICKNAME}送钱吗")
    except:
        await PMove.finish("汇款额只能是数字")

    qq = get_message_at(event.json())
    if len(qq) > 0:
        toqq = qq[0]
    else:
        await PMove.finish("倒是@你要汇款的人啊")

    uid = event.user_id
    # 防止转账对象是自己
    if toqq == uid:
        await PMove.finish("你要给自己汇款？你信不信我能把你钱全吞了")

    group = event.group_id
    money = await BagUser.get_gold(uid, group)
    charges = int(num * 0.05) if int(num * 0.05) > 1 else 1
    if num + charges > money * 0.3:
        await PMove.finish(f"单次转账不得超过手头资产的30%")
    if num > money:
        await PMove.finish(f"你的钱好像不够啊")
    else:
        gold = await BagUser.get_gold(toqq, group)
        inbank_to = await TZBank.get(toqq, group)
        all = gold + inbank_to
        CanSave = all * 0.7 - inbank_to
        if CanSave >= num:
            max_money = await calculation_max_money(toqq, group)
            if inbank_to + num - charges > max_money:
                CanSave = int((max_money - inbank_to) * 1.05)
                await PMove.finish(
                    f"转入失败\n转入超过对方银行上限\n提高跟{NICKNAME}的好感度能增加上限哦\n还可转入：{int(CanSave) if int(CanSave) > 0 else 0}")
            else:
                await BagUser.spend_gold(uid, group, num)
                await TZBank.add(toqq, group, num - charges)
                await TZtreasury.add(group, charges)
                quchu_num = await check_bank_70(uid, group)
                if quchu_num:
                    await PTP.finish(
                        f"{num}成功转入\n{NICKNAME}收取了2%({charges})的手续费\n转入后银行存款超出已拥有的百分之70\n已自动取出{quchu_num}到余额\n收取百分7%手续费")
                await PMove.finish(f"{num}成功转入对方的银行账户\n{NICKNAME}收取了5%({charges})的手续费")

        else:
            await PMove.finish(f"转入失败\n转入超过对方拥有总额的70%\n当前最大可转入{int(CanSave) if int(CanSave) > 0 else 0}")


PTP = on_command("#个人转账", priority=5, permission=GROUP, block=True)


@PTP.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await PTP.finish(f"转账额一金币都不到你要干啥")
        elif num == 1:
            await PTP.finish(f"最低手续费要一金币哟，你要给{NICKNAME}送钱吗")
    except:
        await PTP.finish("转账额只能是数字")

    qq = get_message_at(event.json())
    if len(qq) > 0:
        toqq = qq[0]
    else:
        await PTP.finish("倒是@你要转账的人啊")

    uid = event.user_id
    # 防止转账对象是自己
    if toqq == uid:
        await PTP.finish("你要给自己转账？你信不信我能把你钱全吞了")

    group = event.group_id
    money = await BagUser.get_gold(uid, group)
    charges = int(num * 0.02) if int(num * 0.02) > 1 else 1
    if num > money * 0.7:
        await PTP.finish(f"单次转账不得超过手头资产的70%")
    if num > money:
        await PTP.finish(f"你的钱好像不够啊")
    else:
        await BagUser.spend_gold(uid, group, num)
        await BagUser.add_gold(toqq, group, num - charges)
        await TZtreasury.add(group, charges)
        quchu_num = await check_bank_70(uid, group)
        if quchu_num:
            await PTP.finish(
                f"{num}成功转入\n{NICKNAME}收取了2%({charges})的手续费\n转入后银行存款超过拥有总额的70%\n已自动取出{quchu_num}到余额\n收取百分7%手续费")
        await PTP.finish(f"{num}成功转入\n{NICKNAME}收取了2%({charges})的手续费")


mySave = on_command("#我的存款", aliases={"#银行存款"}, priority=5, permission=GROUP, block=True)


@mySave.handle()
async def _(event: GroupMessageEvent):
    money = await TZBank.get(event.user_id, event.group_id)
    await mySave.finish(f"你在{NICKNAME}的银行存款共有\n{money}枚金币")


updateSave = on_command("#更新存款", permission=SUPERUSER, block=True)


@updateSave.handle()
async def _():
    await update_bank_gold()
    await mySave.finish(f"更新成功")


# 参照 shop/gold.py
rank = on_command("#存款排行", priority=5, permission=GROUP, block=True)


@rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    num = arg.extract_plain_text().strip()

    if is_number(num) and 51 > int(num) > 10:
        num = int(num)
    else:
        num = 10

    all_users = await TZBank.get_all_users(event.group_id)
    all_user_id = [user.user_qq for user in all_users]
    all_user_data = [user.money for user in all_users]

    rank_image = await init_rank("存款排行", all_user_id, all_user_data, event.group_id, num)

    if rank_image:
        await rank.finish(image(b64=rank_image.pic2bs4()))


async def update_bank_gold():
    all_users = await TZBank.get_all_users()
    for q in all_users:
        uid = q.user_qq
        group = q.group_id
        max_money = await calculation_max_money(uid, group)
        if q.money > max_money:
            await TZBank.spend(uid, group, q.money - max_money)
            await BagUser.add_gold(uid, group, q.money - max_money)
        await check_bank_70(uid, group)


# 自动更新
async def update_bank_70():
    all_users = await TZBank.get_all_users()
    for q in all_users:
        await check_bank_70(q.user_qq, q.group_id)


async def check_bank_70(user_qq: int, group_id: int):
    gold = await BagUser.get_gold(user_qq, group_id)
    inbank = await TZBank.get(user_qq, group_id)
    all = gold + inbank
    CanSave_bank = int(all * 0.7)
    if inbank == 1:
        return False
    if CanSave_bank < inbank:
        num = inbank - CanSave_bank
        # 手续费
        charges = int(num * 0.07) if int(num * 0.07) > 1 else 1
        if num + charges > inbank:
            return False
        else:
            await TZBank.spend(user_qq, group_id, num + charges)
            await BagUser.add_gold(user_qq, group_id, num)
            await TZtreasury.add(group_id, charges)
            return num


# 计算最大值
async def calculation_max_money(user_qq: int, group_id: int):
    try:
        q = await SignGroupUser.ensure(user_qq, group_id)
        impression = q.impression
    except Exception as e:
        logger.warning(f"{user_qq}该用户未注册")
        impression = 0
    max_money = Config.get_config("TZbank", "MAX_MONEY_BASICS") + int(
        Config.get_config("TZbank", "MAX_MONEY_MULTIPLIER") * impression)
    return int(max_money)
