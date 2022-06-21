from nonebot.adapters.onebot.v11 import  GroupMessageEvent  , Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg
from nonebot import on_command
from utils.utils import get_message_at,is_number
from utils.message_builder import image
from utils.data_utils import init_rank
from configs.config import NICKNAME
from .models.TZtreasuryV1 import TZtreasury
from services.db_context import db
from models.bag_user import BagUser


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
    "cmd": ["#银行存入","#银行取出","#银行汇款","#个人汇款","#个人转账","#我的存款", "#存款排行"],
}

class TZBank(db.Model):
    __tablename__ = "tz_bank"
    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    money = db.Column(db.BigInteger(), default=0)

    _idx1 = db.Index("tz_bank_idx1", "user_qq", "group_id", unique=True)


    @classmethod
    async def spend(cls, uid: int,  group_id: int, num: int):
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money - num).apply()
        else:
            await cls.create( user_qq = uid, group_id=group_id, money= 5 - num)
    
    @classmethod
    async def add(cls, uid: int,  group_id: int, num: int):
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money + num).apply()
        else:
            await cls.create( user_qq = uid, group_id=group_id, money= 5 + num)

    @classmethod
    async def get(cls, uid: int,  group_id: int):
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            return my.money
        else:
            await cls.create( user_qq = uid, group_id=group_id, money = 5)
            return 5

    @classmethod
    async def get_all_users(cls, group_id: int):
        if not group_id:
            query = await cls.query.gino.all()
        else:
            query = await cls.query.where((cls.group_id == group_id)).gino.all()
        return query

save = on_command("#银行存入", priority=5,permission=GROUP, block=True)
@save.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg =  arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"连一金币都不存你要干啥")
    except:
        await save.finish("存款额只能是数字")

    uid = event.user_id
    group = event.group_id
    gold = await BagUser.get_gold(uid, group)
    inbank = await TZBank.get(uid, group)
    all = gold + inbank

    CanSave = all*0.7 - inbank - 3
    if CanSave >= num :
        if gold < num*1.03:
            await save.finish(f"你的钱好像不够啊")
        else:
            await BagUser.spend_gold(uid, group,int(num*1.03))
            await TZtreasury.add(group,int(num*0.03))
            await TZBank.add(uid, group,num)
            await save.finish(f"{num}成功存入\n{NICKNAME}收取了3%({int(num*0.03)})的手续费")
    else:
        await save.finish(f"你还可以存入{int(CanSave)}")


take = on_command("#银行取出", priority=5,permission=GROUP, block=True)
@take.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg =  arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"连一金币都不取你要干啥")
    except:
        await save.finish("取款额只能是数字")
        
    uid = event.user_id
    group = event.group_id
    inbank = await TZBank.get(uid, group)

    if num > inbank*1.07:
        await save.finish(f"你的钱好像不够啊")
    else:
        await TZBank.spend(uid, group,int(num*1.07))
        await BagUser.add_gold(uid, group,num)
        await TZtreasury.add(group,int(num*0.07))
        await save.finish(f"{num}成功取出\n{NICKNAME}收取了7%({int(num*0.07)})的手续费")

bankMove = on_command("#银行汇款", priority=5,permission=GROUP, block=True)
@bankMove.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg =  arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"汇款额一金币都不到你要干啥")
    except:
        await save.finish("汇款额只能是数字")
    
    qq = get_message_at(event.json())
    if len(qq)>0:
        toqq = qq[0]
    else:
        await save.finish("倒是@你要汇款的人啊")

    uid = event.user_id
    #防止转账对象是自己
    if toqq == uid:
        await save.finish("你要给自己汇款？你信不信我能把你钱全吞了")

    
    group = event.group_id
    inbank = await TZBank.get(uid, group)

    if num*1.01 > inbank:
        await save.finish(f"你的钱好像不够啊")
    else:
        await TZBank.spend(uid, group,int(num*1.01))
        await TZBank.add(toqq, group ,num)
        await TZtreasury.add(group,int(num*0.01))
        await save.finish(f"{num}成功转入对方的银行账户\n{NICKNAME}收取了1%({int(num*0.01)})的手续费")


PMove = on_command("#个人汇款", priority=5,permission=GROUP, block=True)
@PMove.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg =  arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"汇款额一金币都不到你要干啥")
    except:
        await save.finish("汇款额只能是数字")
    
    qq = get_message_at(event.json())
    if len(qq)>0:
        toqq = qq[0]
    else:
        await save.finish("倒是@你要汇款的人啊")

    uid = event.user_id
    #防止转账对象是自己
    if toqq == uid:
        await save.finish("你要给自己汇款？你信不信我能把你钱全吞了")

    group = event.group_id
    money = await BagUser.get_gold(uid, group)

    if num > money*0.3:
        await save.finish(f"单次转账不得超过手头资产的30%")

    if num*1.05 > money:
        await save.finish(f"你的钱好像不够啊")
    else:
        await BagUser.spend_gold(uid, group,int(num*1.05))
        await TZBank.add(toqq, group, num)
        await TZtreasury.add(group,int(num*0.05))
        await save.finish(f"{num}成功转入对方的银行账户\n{NICKNAME}收取了5%({int(num*0.05)})的手续费")

PTP = on_command("#个人转账", priority=5,permission=GROUP, block=True)
@PTP.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg =  arg.extract_plain_text().strip()
    try:
        num = int(msg)
        if num < 1:
            await save.finish(f"转账额一金币都不到你要干啥")
    except:
        await save.finish("转账额只能是数字")
    
    qq = get_message_at(event.json())
    if len(qq)>0:
        toqq = qq[0]
    else:
        await save.finish("倒是@你要转账的人啊")
    
    
    uid = event.user_id
    #防止转账对象是自己
    if toqq == uid:
        await save.finish("你要给自己转账？你信不信我能把你钱全吞了")

    group = event.group_id
    money = await BagUser.get_gold(uid, group)

    if num > money*0.7:
        await save.finish(f"单次转账不得超过手头资产的70%")

    if num*1.02 > money:
        await save.finish(f"你的钱好像不够啊")
    else:
        await BagUser.spend_gold(uid, group,int(num*1.02))
        await BagUser.add_gold(toqq, group,num)
        await TZtreasury.add(group,int(num*0.02))
        await save.finish(f"{num}成功转入对方的银行账户\n{NICKNAME}收取了2%({int(num*0.02)})的手续费")

mySave = on_command("#我的存款", priority=5,permission=GROUP, block=True)
@mySave.handle()
async def _(event: GroupMessageEvent):
    money = await TZBank.get(event.user_id, event.group_id)
    await mySave.finish(f"你在{NICKNAME}的银行存款共有\n{money}枚金币")

#参照 shop/gold.py
rank = on_command("#存款排行", priority=5,permission=GROUP, block=True)
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