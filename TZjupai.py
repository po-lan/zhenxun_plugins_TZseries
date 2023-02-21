from utils.http_utils import AsyncHttpx
from nonebot.adapters.onebot.v11 import Message 
from nonebot.params import CommandArg
from nonebot import on_command
from utils.message_builder import image

__zx_plugin_name__ = "小人举牌"
__plugin_usage__ = """
usage：
    生成举牌小人
    指令：
        小人举牌 文本[max=32]
""".strip()
__plugin_des__ = "生成举牌小人"
__plugin_cmd__ = ["小人举牌 文本"]
__plugin_type__ = ("一些工具",2)
__plugin_version__ = 1.0
__plugin_author__ = "落灰"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["小人举牌"],
}
jupai = on_command("小人举牌", priority=5, block=True)
@jupai.handle()
async def _(arg: Message = CommandArg()):
    text = arg.extract_plain_text().strip()
    if text == "":
        await jupai.finish("你要举什么，你倒是带上啊")
        return
    if len(text) > 32:
        text = text[0:32]
    r = await AsyncHttpx.post(
        "https://www.jiuwa.net/tools/jupai/index.php",
        data={"t":text},
        verify=False
    )
    url = "https://www.jiuwa.net"+r.text

    if url:
        await jupai.finish(image(url))
    else:
        await jupai.send("举牌失败")