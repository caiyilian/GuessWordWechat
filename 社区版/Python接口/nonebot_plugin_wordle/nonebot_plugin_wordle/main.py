import json
import random
from io import BytesIO
from pathlib import Path
from enum import Enum
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont
from spellchecker import SpellChecker
from typing import Optional
# 辅助函数和类
data_dir = Path(__file__).parent / "resources"
fonts_dir = data_dir / "fonts"
words_dir = data_dir / "words"

spell = SpellChecker()

def legal_word(word: str) -> bool:
    return not spell.unknown((word,))

def random_word(dic_name: str = "CET4", word_length: int = 5):
    with (words_dir / f"{dic_name}.json").open("r", encoding="utf-8") as f:
        data: dict = json.load(f)
        data = {k: v for k, v in data.items() if len(k) == word_length}
        word = random.choice(list(data.keys()))
        meaning = data[word]["中释"]
        return word, meaning

def save_png(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGBA")
    frame.save(output, format="png")
    return output

def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")

# 猜单词游戏类
class GuessResult(Enum):
    WIN = 0  # 猜出正确单词
    LOSS = 1  # 达到最大可猜次数，未猜出正确单词
    DUPLICATE = 2  # 单词重复
    ILLEGAL = 3  # 单词不合法

class Wordle:
    def __init__(self, word: str, meaning: str):
        self.word: str = word  # 单词
        self.meaning: str = meaning  # 单词释义
        self.result = f"【单词】：{self.word}\n【释义】：{self.meaning}"
        self.word_lower: str = self.word.lower()
        self.length: int = len(word)  # 单词长度
        self.rows: int = self.length + 1  # 可猜次数
        self.guessed_words: list[str] = []  # 记录已猜单词

        self.block_size = (40, 40)  # 文字块尺寸
        self.block_padding = (10, 10)  # 文字块之间间距
        self.padding = (20, 20)  # 边界间距
        self.border_width = 2  # 边框宽度
        self.font_size = 20  # 字体大小
        self.font = load_font("KarnakPro-Bold.ttf", self.font_size)

        self.correct_color = (134, 163, 115)  # 存在且位置正确时的颜色
        self.exist_color = (198, 182, 109)  # 存在但位置不正确时的颜色
        self.wrong_color = (123, 123, 124)  # 不存在时颜色
        self.border_color = (123, 123, 124)  # 边框颜色
        self.bg_color = (255, 255, 255)  # 背景颜色
        self.font_color = (255, 255, 255)  # 文字颜色

    def guess(self, word: str) -> Optional[GuessResult]:
        word = word.lower()
        if word == self.word_lower:
            self.guessed_words.append(word)
            return GuessResult.WIN
        if word in self.guessed_words:
            return GuessResult.DUPLICATE
        if not legal_word(word):
            return GuessResult.ILLEGAL
        self.guessed_words.append(word)
        if len(self.guessed_words) == self.rows:
            return GuessResult.LOSS

    def draw_block(self, color, letter: str):
        block = Image.new("RGB", self.block_size, self.border_color)
        inner_w = self.block_size[0] - self.border_width * 2
        inner_h = self.block_size[1] - self.border_width * 2
        inner = Image.new("RGB", (inner_w, inner_h), color)
        block.paste(inner, (self.border_width, self.border_width))
        if letter:
            letter = letter.upper()
            draw = ImageDraw.Draw(block)
            bbox = self.font.getbbox(letter)
            x = (self.block_size[0] - bbox[2]) / 2
            y = (self.block_size[1] - bbox[3]) / 2
            draw.text((x, y), letter, font=self.font, fill=self.font_color)
        return block

    def draw(self) -> BytesIO:
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.rows * self.block_size[1]
        board_h += (self.rows - 1) * self.block_padding[1] + 2 * self.padding[1]
        board_size = (board_w, board_h)
        board = Image.new("RGB", board_size, self.bg_color)

        for row in range(self.rows):
            if row < len(self.guessed_words):
                guessed_word = self.guessed_words[row]

                word_incorrect = ""  # 猜错的字母
                for i in range(self.length):
                    if guessed_word[i] != self.word_lower[i]:
                        word_incorrect += self.word_lower[i]
                    else:
                        word_incorrect += "_"  # 猜对的字母用下划线代替

                blocks: list[IMG] = []
                for i in range(self.length):
                    letter = guessed_word[i]
                    if letter == self.word_lower[i]:
                        color = self.correct_color
                    elif letter in word_incorrect:
                        word_incorrect = word_incorrect.replace(letter, "_", 1)
                        color = self.exist_color
                    else:
                        color = self.wrong_color
                    blocks.append(self.draw_block(color, letter))

            else:
                blocks = [
                    self.draw_block(self.bg_color, "") for _ in range(self.length)
                ]

            for col, block in enumerate(blocks):
                x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * col
                y = self.padding[1] + (self.block_size[1] + self.block_padding[1]) * row
                board.paste(block, (x, y))
        return save_png(board)

    def get_hint(self) -> str:
        letters = set()
        for word in self.guessed_words:
            for letter in word:
                if letter in self.word_lower:
                    letters.add(letter)
        return "".join([i if i in letters else "*" for i in self.word_lower])

    def draw_hint(self, hint: str) -> BytesIO:
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.block_size[1] + 2 * self.padding[1]
        board = Image.new("RGB", (board_w, board_h), self.bg_color)

        for i in range(len(hint)):
            letter = hint[i].replace("*", "")
            color = self.correct_color if letter else self.bg_color
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(self.draw_block(color, letter), (x, y))
        return save_png(board)

# 命令行交互逻辑
def main():
    word, meaning = random_word()
    print(word)
    game = Wordle(word, meaning)
    print(f"你有{game.rows}次机会猜出单词，单词长度为{game.length}，请发送单词")

    while True:
        guess = input("请输入你的猜测: ").strip()
        result = game.guess(guess)

        if result == GuessResult.WIN:
            print(f"恭喜你猜出了单词！\n{game.result}")
            break
        elif result == GuessResult.LOSS:
            print(f"很遗憾，没有猜出来呢\n{game.result}")
            break
        elif result == GuessResult.DUPLICATE:
            print("你已经猜过这个单词了呢")
        elif result == GuessResult.ILLEGAL:
            print(f"你确定 {guess} 是一个合法的单词吗？")
        else:
            print("继续猜吧！")

if __name__ == "__main__":
    main()