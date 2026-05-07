"""输入去噪器 - 清洗用户输入中的噪声字符"""

import re
import unicodedata
from typing import Optional
from project.logger_handler import logger


class InputDenoiser:
    """用户输入去噪处理器"""

    def __init__(self, config: Optional[dict] = None):
        self._config = config or {}
        self._zero_width_pattern = re.compile(
            "[\u200b\u200c\u200d\u200e\u200f\uFEFF\u00AD]"
        )
        self._control_char_pattern = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    @staticmethod
    def _fullwidth_to_halfwidth(text: str) -> str:
        """全角数字/字母 → 半角"""
        result = []
        for ch in text:
            code = ord(ch)
            # 全角数字和字母范围：FF00-FFEF
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            elif code == 0x3000:  # 全角空格
                result.append(" ")
            else:
                result.append(ch)
        return "".join(result)

    def denoise(self, raw_input: str) -> str:
        """去噪主入口

        处理步骤：
        1. 移除控制字符和零宽字符
        2. 连续空白合并为单个空格
        3. 全角数字/字母 → 半角
        4. 连续相同字符截断（如"啊啊啊啊" → "啊啊"）
        5. 去除首尾连续标点噪声
        6. strip
        """
        if not raw_input:
            return ""

        cfg = self._config
        text = raw_input

        # 1. 移除控制字符 (\x00-\x1f) 和零宽字符
        text = self._control_char_pattern.sub("", text)
        text = self._zero_width_pattern.sub("", text)

        # 2. 连续空白合并为单个空格
        text = re.sub(r"\s+", " ", text)

        # 3. 全角 → 半角
        if cfg.get("fullwidth_to_halfwidth", True):
            text = self._fullwidth_to_halfwidth(text)

        # 4. 连续相同字符截断（max_repeat_chars 个）
        max_repeat = cfg.get("max_repeat_chars", 2)
        if max_repeat and max_repeat > 0:
            text = re.sub(r"(.)\1{" + str(max_repeat) + r",}", r"\1" * max_repeat, text)

        # 5. 去除首尾连续标点噪声（如 "！！！你好。。。" → "你好"）
        if cfg.get("strip_noise_punctuation", True):
            text = re.sub(r"^[^\w\u4e00-\u9fff]+", "", text)
            text = re.sub(r"[^\w\u4e00-\u9fff]+$", "", text)

        # 6. strip
        text = text.strip()

        # fallback: 去噪结果为空 → 返回 raw_input.strip()
        if not text:
            logger.warning("[InputDenoiser] 去噪结果为空，返回原始输入")
            return raw_input.strip()

        return text


# 延迟初始化单例（首次 import 时 config 可能未加载）
input_denoiser: Optional[InputDenoiser] = None


def init_denoiser(config: dict):
    """初始化去噪器单例"""
    global input_denoiser
    input_denoiser = InputDenoiser(config)
    logger.info("[InputDenoiser] 去噪器初始化完成")
