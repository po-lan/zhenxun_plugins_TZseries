from nonebot import Driver
from utils.decorator.shop import shop_register
from models.bag_user import BagUser
import nonebot
import random

# 判断当前插件是否放在TZ系列插件目录下
TZ = False
try:
    from ._model import TZtreasury
    TZ = True
except :
    TZ = False

# @
# @简介：一个很简单的坑钱罐子，有几率从里面开出远超购买罐子的金币，联动了堂主系列插件的小金库，使用罐子后购买罐子的钱将流入真寻小金库
# @参数修改：prob既为回本概率，罐子内最小金额和最大金额均可修改，修改对应字典值即可，修改后需要重启真寻才能生效
# @作者：Syozhi
# @邮箱：Syozhi@163.com
# @版本：v1.0
# @

driver: Driver = nonebot.get_driver()

@driver.on_startup
async def _():

    # 注册多个
    @shop_register(
        name=("真寻的土制存钱罐", "真寻的银制存钱罐", "真寻的金制存钱罐"),
        price=(100, 200, 500),
        des=("真的有人会拿土做存钱罐吗？", "拿起来发现沉甸甸的，说不定......(回本概率+10%)", "金！金！金！(回本概率+30%)"),
        load_status=(True, True, True),
        daily_limit=(10, 10, 10),
        ** {"真寻的土制存钱罐_prob": 0.05, "真寻的银制存钱罐_prob": 0.15, "真寻的金制存钱罐_prob": 0.35},
    )
    async def sign_piggy(goods_name: str, user_id: int, group_id: int, prob: float):
        # 每个存钱罐的最小储币量
        goods_minGold = {"真寻的土制存钱罐": 0, "真寻的银制存钱罐": 2, "真寻的金制存钱罐": 10}
        # 每个存钱罐最大储币量
        goods_maxGold = {"真寻的土制存钱罐": 200, "真寻的银制存钱罐": 400, "真寻的金制存钱罐": 1000}
        # 当前存钱罐本金
        goods_price = {"真寻的土制存钱罐": 100, "真寻的银制存钱罐": 200, "真寻的金制存钱罐": 500}
        # 是否回本
        flag_huiben = False
        # 开罐
        rush = random.random()
        if rush<=prob : flag_huiben = True
        if flag_huiben :
            # 回本了
            getGolds = random.randint(goods_price[goods_name]-1, goods_maxGold[goods_name]+1)
        else :
            # 亏了
            getGolds = random.randint(goods_minGold[goods_name],goods_price[goods_name])

        # 使用道具的描述
        use_str = (f"你抄起{goods_name}往地上重重砸去\n{getGolds}枚金币散落在地上",
                   f"你抡起大锤一下把{goods_name}砸得稀巴烂\n{getGolds}枚金币像烟花一样在你眼前散开",
                   f"你抡起大锤重重的向{goods_name}锤去，你并没有锤中罐子，但罐子的盖子被你震开了\n你获得了{getGolds}枚金币",
                   f"你打开{goods_name}的盖子将里面的金币全部倒了出来\n你数了数一共有{getGolds}枚金币",
                   f"你摩擦着{goods_name}的外壁心里默念着什么，随后你轻轻打打开盖子\n罐子里有{getGolds}枚金币",
                   f"你试着摇晃罐子，听到里面叮叮当当的声音，于是兴奋的打开盖子\n你定眼一看，{getGolds}枚金币出现在你眼前",
                   f"你以迅雷不及掩耳盗铃之势将{goods_name}的盖子打开\n你获得了{getGolds}枚金币",
                   f"你把{goods_name}交给了你的非洲朋友，他疑惑的看了你一眼随后打开了盖子\n他为你开出了{getGolds}枚金币",
                   f"你把{goods_name}交给了你的欧洲朋友，他漫不经心的打开了盖子\n他为你开出了{getGolds}枚金币",
                   f"{goods_name}的盖子太紧了，你找来了撬棍，废了九牛二虎之力终于撬开了罐子\n你获得了{getGolds}枚金币"
                   )
        # 玩家获得金币
        await BagUser.add_gold(user_id, group_id, getGolds)

        # 买罐子的钱收入真寻小金库(如果有打TZ插件的话)
        if TZ :
            await TZtreasury.update_treasury_info(group_id, goods_price[goods_name])
        str_out = use_str[random.randint(0, len(use_str)-1)]
        return str_out      # 返回值将作为提示内容输出，也可以返回None，在sign_card中使用bot发送消息


