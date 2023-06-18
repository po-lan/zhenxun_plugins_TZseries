from services.db_context import Model
import datetime
from tortoise import fields
from typing import List, Optional, Tuple


def BeforeDay():
    return (datetime.datetime.now() - datetime.timedelta(days=1))


class TZtreasury(Model):
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    group_id = fields.BigIntField()
    """群聊id"""
    money = fields.BigIntField()

    class Meta:
        table = "tz_treasury"
        table_description = "乞讨福利金表"
        unique_together = ("id", "group_id")

    @classmethod
    async def update_treasury_info(
            cls,
            group_id: int,
            num: int,
    ):
        """
        说明:
            修改福利金数量
        参数:
            :param group_id: 群组id
            :param num: 福利金增减的数量
        """
        my = await cls.get_or_none(group_id=group_id)
        if my:
            await my.update_or_create(group_id=group_id, defaults={"money": my.money + num})
        else:
            await cls.create(group_id=group_id, money=1000 + num)

    @classmethod
    async def get_group_treasury(cls, group_id: int):
        my = await cls.filter(group_id=group_id).first()
        if my:
            return my.money
        else:
            await cls.create(group_id=group_id, money=10000)
            return 10000


class TZBank(Model):
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    user_qq = fields.BigIntField()
    group_id = fields.BigIntField()
    money = fields.BigIntField(default=0)

    class Meta:
        table = "tz_bank"
        table_description = "银行表"
        unique_together = ("user_qq", "group_id")

    @classmethod
    async def update_bank_info(
            cls,
            user_qq: int,
            group_id: int,
            num: int,
    ):
        """
        说明:
            修改银行金币
        参数:
            :param user_qq: 用户id
            :param group_id: 群组id
            :param num: 金币增减的数量
        """
        my = await cls.get_or_none(group_id=group_id, user_qq=user_qq)
        money = my.money if my else 0
        await cls.update_or_create(group_id=group_id, user_qq=user_qq, defaults={"money": money + num})

    @classmethod
    async def get_(cls, uid: int, group_id: int):
        my = await cls.get_or_none(group_id=group_id, user_qq=uid)
        if my:
            return my.money
        else:
            return 0

    @classmethod
    async def get_all_users(cls, group_id: int = None):
        if not group_id:
            query = await cls.all()
        else:
            query = await cls.filter(group_id=group_id).first()
        return query


class TZBlack(Model):
    __tablename__ = "tz_black"
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    uid = fields.BigIntField()
    from_qq = fields.BigIntField()
    gid = fields.BigIntField()
    money = fields.BigIntField(default=0)
    inMoney = fields.BigIntField(default=0)
    state = fields.IntField(default=0)
    initime = fields.DatetimeField(null=True)
    wrtime = fields.DatetimeField(null=True)

    # time = db.Column(db.DateTime(), server_default='now()')

    class Meta:
        table = "tz_black"
        table_description = "黑钱表"
        unique_together = ("uid", "gid", "from_qq")

    # 获取24h内所有的黑钱

    @classmethod
    async def get_my_today_all(cls, uid, gid: int = None):
        if gid == None:
            return 0
        query = await cls.filter(gid=gid, uid=uid, initime__gte=BeforeDay()).all()
        mList = [x.money if x.inMoney == 0 else x.inMoney for x in query]
        return sum(mList) if len(mList) > 0 else 0

    # 获取24h内所有没有洗白的黑钱
    @classmethod
    async def get_my_today_all_isBlock(cls, uid, gid: int = None):
        if gid == None:
            return 0
        query = await cls.filter(gid=gid, uid=uid, initime__gte=BeforeDay(), state=0).all()
        mList = [x.money if x.inMoney == 0 else x.inMoney for x in query]
        return sum(mList) if len(mList) > 0 else 0

    # 获取24h内 所有 来源于我的黑钱
    @classmethod
    async def get_Frome_today_all(cls, from_qq, gid: int = None):
        if gid == None:
            return 0
        query = await cls.filter(gid=gid, from_qq=from_qq, initime__gte=BeforeDay()).all()
        return sum([x.money for x in query])

    # 获取24h内 所有 来源于我 的还没洗白的黑钱
    @classmethod
    async def get_Frome_today_all_isBlock(cls, from_qq, gid: int = None):
        if gid == None:
            return 0
        query = await cls.filter(gid=gid, from_qq=from_qq, initime__gte=BeforeDay(), state=0).all()
        return sum([x.money for x in query])

    # 新增黑钱
    @classmethod
    async def add_blackMoney(cls, uid, from_qq, num, inNum=0, gid: int = None):
        if gid == None:
            return 0
        user, _ = await cls.get_or_create(uid=uid, gid=gid, from_qq=from_qq)
        if user.inMoney < 0:
            await cls.update_or_create(uid=uid, gid=gid, from_qq=from_qq, defaults={"money":user.money+num, "inMoney":inNum, "state":0, "initime":datetime.datetime.now()})
        else:
            await cls.update_or_create(uid=uid, gid=gid, from_qq=from_qq, defaults={"money":user.money+num, "inMoney":user.inMoney+inNum, "state":0, "initime":datetime.datetime.now()})

    # 洗白标记
    @classmethod
    async def all_toW(cls, uid, gid: int = None):
        if gid == None:
            return 0
        await cls.filter(uid=uid, gid=gid).update(money=0,inMoney=0,state=1, wrtime=datetime.datetime.now())

    # 一定时间内是否 洗白过
    @classmethod
    async def before_Time_Has(cls, uid, gid, time=18 * 60):
        if gid == None:
            return 0
        bTime = (datetime.datetime.now() - datetime.timedelta(minutes=time))
        user = await cls.filter(uid=uid, state=1, wrtime__not_isnull=True, wrtime__gt=bTime).first()
        # 如果在 这段时间内有过洗白就 返回True
        if user:
            return True
        return False

    @classmethod
    # 获取 超过 24h 没有洗白的钱
    async def Over24_block_money(cls):
        bTime = (datetime.datetime.now() - datetime.timedelta(days=1))
        query = await cls.filter(state=0, initime__lt=bTime).all()
        return query

    @classmethod
    # 获取 追回 24h 没有洗白的钱 标记
    async def Over24_block_isBack(cls, id_):
        await cls.filter(id=id_).update(money=0,inMoney=0,state=2, wrtime=datetime.datetime.now())
