"""Gate: traditional_chinese."""
from __future__ import annotations
from typing import Optional
from .base import Gate, Violation

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


class TraditionalChineseGate(Gate):
    """Detect traditional Chinese characters in otherwise-simplified output.

    Uses a built-in reference set of common traditional characters
    (extensible via ``extra_chars`` in config). Any match triggers
    a violation — the assistant should rewrite with simplified Chinese.
    """

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        extra = set(cfg.get("extra_chars", []))
        char_set = _DEFAULT_TRADITIONAL_CHARS | extra

        found: list[str] = []
        seen: set[str] = set()
        for ch in response_text:
            if ch in char_set and ch not in seen:
                found.append(ch)
                seen.add(ch)
                if len(found) >= 20:  # cap report at 20 unique chars
                    break

        if found:
            return Violation(
                gate_name=self.name,
                description=self.description,
                details=(
                    f"Found {len(found)} traditional Chinese char(s): "
                    f"{', '.join(found)}"
                ),
                action=self.action,
            )
        return None


