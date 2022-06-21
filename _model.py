from services.db_context import db


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
            await  my.update(money=my.money + num).apply()
        else:
            await cls.create(group_id=group_id, money=10000 + num)

    @classmethod
    async def set(cls, group_id: int, num: int):
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await  my.update(money=num).apply()
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
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money - num).apply()
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5 - num)

    @classmethod
    async def add(cls, uid: int, group_id: int, num: int):
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            await my.update(money=my.money + num).apply()
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5 + num)

    @classmethod
    async def get(cls, uid: int, group_id: int):
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()

        if my:
            return my.money
        else:
            await cls.create(user_qq=uid, group_id=group_id, money=5)
            return 5

    @classmethod
    async def get_all_users(cls, group_id: int):
        if not group_id:
            query = await cls.query.gino.all()
        else:
            query = await cls.query.where((cls.group_id == group_id)).gino.all()
        return query

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