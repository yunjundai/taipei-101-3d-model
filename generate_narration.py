#!/usr/bin/env python3
"""
Generate natural Taiwanese Mandarin female neural voiceovers (zh-TW-HsiaoChenNeural)
for all 7 chapters of the Taipei 101 3D explainer animation.
"""

import asyncio
import json
from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "narration"
VOICE = "zh-TW-HsiaoChenNeural"
RATE = "-4%"
PITCH = "+0Hz"

# Spoken scripts tailored for natural Taiwanese Mandarin pronunciation
SCRIPTS = [
    (
        "ch01",
        "台北一零一，位於台北信義計畫區，於二零零四年正式落成。建築總高度達五百零八點二公尺，地上共一百零一層、地下五層，曾蟬聯世界第一高樓長達六年，是台灣最具代表性的城市地標。",
    ),
    (
        "ch02",
        "建築底部由階梯式花崗岩廣場、東側六層購物中心裙樓，以及一到二十五樓向上內收的梯形塔座所組成。外觀形如穩固的寶鼎，為上方高聳的塔身，奠定紮實的視覺與結構基礎。",
    ),
    (
        "ch03",
        "在底座與主塔交界的二十六樓四面立面，鑲嵌著直徑超過十公尺的巨型古銅錢，並搭配各節轉角的祥雲如意裝飾，將中華文化中招財納福的寓意，巧妙轉化為現代摩天建築語彙。",
    ),
    (
        "ch04",
        "主塔由八個每節八層的倒梯形單元層層疊起，呼應竹節高升與吉祥數字發的意象。四角採用雙重內縮的 W 型鋸齒切角，經風洞實測，可有效削減百分之三十到四十的高空渦流風壓。",
    ),
    (
        "ch05",
        "面對台灣頻繁的地震與颱風，台北一零一在外圍配置八根巨型鋼骨柱，內部灌注一萬 PSI 的高性能混凝土，並每隔八層以巨型桁架串聯中央核心筒，兼顧超高剛性與抗震韌性。",
    ),
    (
        "ch06",
        "懸吊在八十七到九十二樓中央的黃金風阻尼球，由四十一層實心鋼板焊接而成，直徑五點五公尺、重達六百六十公噸。當強風吹襲塔頂時，球體反向擺盪並由底部液壓器耗散能量，可降低高達百分之四十的搖晃幅度。",
    ),
    (
        "ch07",
        "登上八十九樓室內觀景台與九十一樓戶外平台，就能三百六十度俯瞰大台北盆地。每年跨年夜，台北一零一更化身全球注目的立體煙火舞台，以璀璨火光點亮夜空，展現台灣的工程美學與城市活力。",
    ),
]


async def synth_all() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, text in SCRIPTS:
        mp3_path = OUT_DIR / f"{key}.mp3"
        comm = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)
        await comm.save(str(mp3_path))
        duration = round(MP3(str(mp3_path)).info.length, 2)
        manifest.append(
            {
                "id": key,
                "file": f"narration/{key}.mp3",
                "voice": VOICE,
                "duration": duration,
                "size_bytes": mp3_path.stat().st_size,
            }
        )
        print(f"Generated {mp3_path.name}: {duration:.2f}s ({mp3_path.stat().st_size:,} bytes)")

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved manifest: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(synth_all())
