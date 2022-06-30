from services.db_context import db
import datetime


def BeforeDay():
    return (datetime.datetime.now()-datetime.timedelta(days=1))


class TZtreasury(db.Model):
    __tablename__ = "tz_treasury"

    id = db.Column(db.Integer(), primary_key=True)
    group_id = db.Column(db.BigInteger(), nullable=False)
    money = db.Column(db.BigInteger(), nullable=False, default=0)

    _idx1 = db.Index("tz_treasury_idx1", "group_id", unique=True)

    @classmethod
    async def spend(cls, group_id: int, num: int):
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money + num).apply()
        else:
            await cls.create(group_id=group_id, money=10000 - num)

    @classmethod
    async def add(cls, group_id: int, num: int):
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money + num).apply()
        else:
            await cls.create(group_id=group_id, money=10000 + num)

    @classmethod
    async def set(cls, group_id: int, num: int):
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=num).apply()
        else:
            await cls.create(group_id=group_id, money=10000 + num)

    @classmethod
    async def get(cls, group_id: int):
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            return my.money
        else:
            await cls.create(group_id=group_id, money=10000)
            return 10000


class TZBank(db.Model):
    __tablename__ = "tz_bank"
    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    money = db.Column(db.BigInteger(), default=0)

    _idx1 = db.Index("tz_bank_idx1", "user_qq", "group_id", unique=True)

    @classmethod
    async def spend(cls, uid: int, group_id: int, num: int):
        query = cls.query.where((cls.user_qq == uid) &
                                (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money - num).apply()
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5 - num)

    @classmethod
    async def add(cls, uid: int, group_id: int, num: int):
        query = cls.query.where((cls.user_qq == uid) &
                                (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money + num).apply()
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5 + num)

    @classmethod
    async def get(cls, uid: int, group_id: int):
        query = cls.query.where((cls.user_qq == uid) &
                                (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            return my.money
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5)
            return 5

    @classmethod
    async def get_all_users(cls, group_id: int = None):
        if not group_id:
            query = await cls.query.gino.all()
        else:
            query = await cls.query.where((cls.group_id == group_id)).gino.all()
        return query


class TZBlack(db.Model):
    __tablename__ = "tz_black"
    id = db.Column(db.Integer(), primary_key=True)

    uid = db.Column(db.BigInteger(), nullable=False)
    from_qq = db.Column(db.BigInteger(), nullable=False)
    gid = db.Column(db.BigInteger(), nullable=False)

    money = db.Column(db.BigInteger(), default=0)
    state = db.Column(db.Integer(), default=0)
    initime = db.Column(db.DateTime(timezone=True), nullable=False)
    #time = db.Column(db.DateTime(), server_default='now()')

    _idx1 = db.Index("tz_black_idx1", "uid", "gid", "from_qq", unique=True)


    # 获取24h内所有的黑钱
    @classmethod
    async def get_my_today_all(cls, uid, gid: int = None):
        if gid == None:
            return 0
        query = cls.query.where(
            cls.gid == gid and cls.uid == uid and cls.initime >= BeforeDay())
        
        data = await query.with_for_update().gino.all()
        return sum([x.money for x in data])

    # 获取24h内所有没有洗白的黑钱
    @classmethod
    async def get_my_today_all_isBlock(cls, uid, gid: int = None):
        if gid == None:
            return 0
        query = cls.query.where(cls.gid == gid and cls.uid ==
                                uid and cls.initime >= BeforeDay() and cls.state == 0)
        
        data = await query.with_for_update().gino.all()
        return sum([x.money for x in data])

    # 获取24h内 所有 来源于我的黑钱
    @classmethod
    async def get_Frome_today_all(cls, from_qq, gid: int = None):
        if gid == None:
            return 0
        query = cls.query.where(
            cls.gid == gid and cls.from_qq == from_qq and cls.initime >= BeforeDay())
        
        data = await query.with_for_update().gino.all()
        return sum([x.money for x in data])

    # 获取24h内 所有 来源于我 的还没洗白的黑钱
    @classmethod
    async def get_Frome_today_all_isBlock(cls, from_qq, gid: int = None):
        if gid == None:
            return 0
        query = cls.query.where(cls.gid == gid and cls.from_qq ==
                                from_qq and cls.initime >= BeforeDay() and cls.state == 0)
        
        data = await query.with_for_update().gino.all()
        
        return sum([x.money for x in data])

    # 新增黑钱
    @classmethod
    async def add_blackMoney(cls, uid, from_qq, num, gid: int = None):
        if gid == None:
            return 0
        await cls.create(uid=uid, gid=gid, from_qq=from_qq, money=num)


# class TZlottery(db.Model):
#     __tablename__ = "tz_lottery"
#
#     id = db.Column(db.Integer(), primary_key=True)
#     group_id = db.Column(db.BigInteger(), nullable=False)
#     money = db.Column(db.BigInteger(), nullable=False, default=0)
#
#     _idx1 = db.Index("tz_treasury_idx1", "group_id", unique=True)
#
#     @classmethod
#     async def getLotteryGold(cls, group_id: int):
#         query = cls.query.where(cls.group_id == group_id)
#         query = query.with_for_update()
#         my = await query.gino.first()
#
#         if my:
#             return my.money
#         else:
#             await cls.create(group_id=group_id, money=1000)
#             return 1000
#
#     @classmethod
#     async def setLotteryGold(cls, group_id: int, num: int):
#         query = cls.query.where(cls.group_id == group_id)
#         query = query.with_for_update()
#         my = await query.gino.first()
#
#         if my:
#             await my.update(money=num).apply()
#         else:
#             await cls.create(group_id=group_id, money=1000 + num)
