"""Gate: ends_with."""
from __future__ import annotations
from typing import Optional
from .base import Gate, Violation

class EndsWithGate(Gate):
    """Ensure response does not end with prohibited suffixes."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        suffixes = cfg.get("suffixes", [])
        stripped = response_text.rstrip()

        for suffix in suffixes:
            if stripped.endswith(suffix):
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=f"Response ends with: '{suffix}'",
                    action=self.action,
                )
        return None

    def transform(self, response_text: str) -> Optional[str]:
        """Strip the banned suffix from the response text."""
        cfg = self.config.get("config", {})
        suffixes = cfg.get("suffixes", [])
        stripped = response_text.rstrip()
        for suffix in suffixes:
            if stripped.endswith(suffix):
                trailing = response_text[len(stripped):]
                return stripped[: -len(suffix)] + trailing
        return None


# ── Traditional Chinese character set ───────────────────────────────

# Common traditional Chinese characters with their simplified equivalents.
# Built from the Table of General Standard Chinese Characters (通用规范汉字表)
# contrastive pairs. Models occasionally slip traditional chars into
# otherwise-simplified output; this catches them.
_DEFAULT_TRADITIONAL_CHARS: set = set(
    # Only characters with distinct simplified equivalents (not shared forms).
    # Traditional → Simplified pairs from 通用规范汉字表 contrastive set.
    "個們麼這說來時會過開關頭兒長"
    "見貝車門馬魚鳥龍龜風飛"
    "體國書學實寫寶愛戰戲"
    "專創態檔臺爲後"
    "發盡數歲廳應幾"
    "斷曆樓機權殺決沒況準"
    "進運達錢鐵銀銅鋼"
    "電靈靜頁順須顯"
    "東對導從無興"
    "亞萬與業義"
    "將尋異"
    "輕轉農連遊鄉"
    "雲雜錦雖鍾"
    "丟亂乾億僕價"
    "優償嚇壞壓"
    "夠妝孫宮審寵"
    "層屬岡峽帥並廢廣"
    "張強彈徵徹復"
    "憐懷戀戶擁擊擠擬"
    "斂曬殘毀毆氣溝"
    "漢滿漁烏煙煩燒"
    "熱燈爭爺爾牆獲獎獨"
    "現環產當畫療疊"
    "盜眾睜瞭確"
    "禮禍禪稱競筆簡"
    "節範糧糾紀約"
    "紙級紡紋納"
    "純組結絕絲"
    "統經綠緊緒線"
    "術樣"
    "嬪嫻嬈孫"
    "礙礎禮"
    "穩積"
    "貢責"
    "貨貿"
    "質"
)


