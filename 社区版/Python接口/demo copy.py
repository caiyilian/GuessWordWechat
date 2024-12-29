# 如果你是Python36。请删除37、38、39的pyd文件，其他版本同理
# 小提示：因为Pycharm无法识别pyd文件，这句话可能会报红，无视或配置一下就行了，不影响使用
import sys
sys.path.insert(0,r"D:\projects\WeChatPYAPI-master")
import os
# D:\projects\WeChatPYAPI-master\nonebot-plugin-wordle-main\nonebot_plugin_wordle\guess_program.py
from WeChatPYAPI import WeChatPYApi

from nonebot_plugin_wordle.nonebot_plugin_wordle.guess_program import Wordle,random_word,GuessResult
import time
import logging
from queue import Queue



# 当前目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


logging.basicConfig(level=logging.INFO)  # 日志器
msg_queue = Queue()  # 消息队列
target_wxid = ""
lufeng_wxid = ""
img_save_path = r"D:\projects\WeChatPYAPI-master\current_guess\current_guess.png"
usage=(
        "答案为指定长度单词，发送对应长度单词即可；\n"
        "绿色块代表此单词中有此字母且位置正确；\n"
        "黄色块代表此单词中有此字母，但该字母所处位置不对；\n"
        "灰色块代表此单词中没有此字母；\n"
        "猜出单词或用光次数则游戏结束；\n"
        "发送“结束、结束游戏、结束猜单词”均可结束游戏；\n"
    )
def process_msg(msg):
    """
    
    """
    if msg["wx_id"] == target_wxid and msg['is_self_msg'] == 0 and msg['msg_type'] == 1:
        content = msg['content']
        sender = msg['sender'] # 发送者的微信id
        return {
            "content": content,
            "sender": sender
        }
    else:
        return None
        
        
        

def on_message(msg):
    """消息回调，建议异步处理，防止阻塞"""
    msg = process_msg(msg)
    if msg is not None:
        msg_queue.put(msg)


def on_exit(wx_id):
    """退出事件回调"""
    print("微信({})：已退出登录，请重新登录".format(wx_id))
    exit()

def draw_img(img_data):
    with open(img_save_path, "wb") as f:
        f.write(img_data.getbuffer())
    time.sleep(1)

def main():

    # 实例化api对象【要多开的话就实例化多个《WeChatPYApi》对象】
    w = WeChatPYApi(msg_callback=on_message, exit_callback=on_exit, logger=logging)

    # 启动微信【调试模式可不调用该方法】
    errno, errmsg = w.start_wx()
    # errno, errmsg = w.start_wx(path=os.path.join(BASE_DIR, "login_qrcode.png"))  # 保存登录二维码
    if errno != 0:
        print(errmsg)
        if errmsg != "当前为调试模式，不需要调用“start_wx”":
            return

    # 这里需要阻塞，等待获取个人信息
    while not w.get_self_info():
        time.sleep(2)
  
    my_info = w.get_self_info()
    print("登陆成功！")
    lists = w.get_chat_room_members(to_chat_room=target_wxid)
    wxid2name = {}
    for item in lists:
        wxid2name[item['wx_id']] = item['nick_name']

    def send_img(img_data):
        draw_img(img_data)
        w.send_img(
                    to_wx=target_wxid,
                    path=img_save_path
                )
    game_not_running = True
    game = None
    dic_name = "CET4"
    stop_word = ("结束", "结束游戏", "结束猜单词")
    start_time = None
    # 处理消息回调
    while True:
        if game_not_running is False and time.time() - start_time > 300:
            w.send_text(to_wx=target_wxid, msg="猜单词超时(5分钟)，游戏结束\n【单词】：{word}\n【释义】：{meaning}")
            game_not_running = True
            start_time = None
        try:
            msg = msg_queue.get(timeout=1)
        except:
            continue

        content = msg['content']
        sender = msg['sender']
        if content.startswith('猜单词'):
            if len(content) == 3:
                word_length = 5
            elif len(content) > 4 and content[3]==' ':
                num = content[4:]
                if num.isdigit() is False:
                    continue
                word_length = int(num)
                if word_length < 4 or word_length > 8:
                    w.send_text(to_wx=target_wxid, msg="单词长度应在4~8之间")
                    continue
            else:
                continue
            if game_not_running is True:
                game_not_running = False
                word, meaning = random_word(dic_name, word_length)
                game = Wordle(word, meaning)
                w.send_text(to_wx=target_wxid, msg=f"猜单词游戏开始！\n单词长度为{word_length}，\n你有{game.rows}次机会猜出单词。\n{usage}")
                start_time = time.time()
            else:
                w.send_text(to_wx=target_wxid, msg="游戏已经开始了！")
        elif content in stop_word:
            if game_not_running is False:
                game_not_running = True
                game = None
                w.send_text(to_wx=target_wxid, msg=f"游戏已结束\n【单词】：{word}\n【释义】：{meaning}")
        elif content == "提示":
            if game_not_running:
                continue
            hint = game.get_hint()
            if len(hint.replace("*", "")) == 0:
                w.send_text(to_wx=target_wxid, msg="你还没有猜对过一个字母哦~再猜猜吧~")
                continue
            draw_img(game.draw_hint(hint))
            w.send_img(
                to_wx=target_wxid,
                path=img_save_path
            )
        elif content.isalpha() and len(content) == word_length:
            if game_not_running: # 没在运行猜单词游戏
                continue
            result = game.guess(content)
            if result == GuessResult.WIN:
                w.send_text(to_wx=target_wxid, msg=f"恭喜{wxid2name[sender]}猜出单词\n【单词】：{word}\n【释义】：{meaning}")
                send_img(game.draw())
                game_not_running = True
            elif result == GuessResult.LOSS:
                w.send_text(to_wx=target_wxid, msg=f"很遗憾，没有人猜出来呢\n【单词】：{word}\n【释义】：{meaning}")
                game_not_running = True
            elif result == GuessResult.DUPLICATE:
                w.send_text(to_wx=target_wxid, msg="你已经猜过这个单词了。")
            elif result == GuessResult.ILLEGAL:
                w.send_text(to_wx=target_wxid, msg="你输入的不是一个合法的单词。")
            else:
                send_img(game.draw())
            


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os._exit(1)

