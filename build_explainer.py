#!/usr/bin/env python3
"""
Build standalone interactive 3D explainer animation HTML for Taipei 101.
Embeds taipei_101.glb directly as base64 so explainer.html works both via HTTP
and by double-clicking locally without CORS issues.
"""

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GLB_PATH = ROOT / "taipei_101.glb"
NARRATION_DIR = ROOT / "narration"
OUT_PATH = ROOT / "explainer.html"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>台北 101｜3D 建築與工程解說動畫</title>
  <style>
    :root {
      --bg-panel: rgba(9, 15, 28, 0.78);
      --border-panel: rgba(148, 163, 184, 0.22);
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #2dd4bf;
      --accent-warm: #f59e0b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #060b16;
      color: var(--text-main);
      font-family: "Noto Sans TC", "Microsoft JhengHei", "Segoe UI", sans-serif;
      user-select: none;
    }

    #canvas-container {
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100%;
    }

    /* Top bar */
    #topbar {
      position: fixed;
      top: 18px;
      left: 20px;
      right: 20px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      pointer-events: none;
      z-index: 20;
    }

    .brand-card {
      pointer-events: auto;
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      backdrop-filter: blur(12px);
      border-radius: 12px;
      padding: 12px 16px;
      min-width: 240px;
    }

    .brand-tag {
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 4px;
      font-weight: 600;
    }

    .brand-title {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.03em;
      color: #f8fafc;
    }

    .brand-sub {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 3px;
    }

    .top-actions {
      pointer-events: auto;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .pill-btn {
      background: var(--bg-panel);
      color: var(--text-main);
      border: 1px solid var(--border-panel);
      backdrop-filter: blur(10px);
      border-radius: 999px;
      padding: 8px 14px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.18s ease;
    }

    .pill-btn:hover {
      border-color: rgba(45, 212, 191, 0.65);
      background: rgba(15, 28, 48, 0.92);
    }

    .pill-btn.active {
      background: rgba(15, 118, 110, 0.88);
      border-color: var(--accent);
      color: #ffffff;
    }

    /* Right telemetry card */
    #spec-card {
      position: fixed;
      top: 86px;
      right: 20px;
      width: 252px;
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      backdrop-filter: blur(12px);
      border-radius: 12px;
      padding: 14px 16px;
      z-index: 20;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }

    .spec-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }

    .spec-chapter-id {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.12em;
      color: var(--accent);
    }

    .spec-altitude {
      font-size: 12px;
      color: var(--accent-warm);
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    .spec-metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .metric-box {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(148, 163, 184, 0.14);
      border-radius: 8px;
      padding: 8px 10px;
    }

    .metric-label {
      font-size: 10px;
      color: var(--text-muted);
      margin-bottom: 3px;
    }

    .metric-value {
      font-size: 14px;
      font-weight: 700;
      color: #f8fafc;
      font-variant-numeric: tabular-nums;
    }

    /* Altitude ruler on left */
    #alt-ruler {
      position: fixed;
      left: 20px;
      top: 50%;
      transform: translateY(-50%);
      height: 290px;
      width: 58px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: flex-start;
      pointer-events: none;
      z-index: 15;
    }

    .ruler-track {
      position: absolute;
      left: 6px;
      top: 6px;
      bottom: 6px;
      width: 2px;
      background: rgba(148, 163, 184, 0.28);
      border-radius: 2px;
    }

    #ruler-indicator {
      position: absolute;
      left: 1px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 12px rgba(45, 212, 191, 0.9);
      transform: translateY(-50%);
      transition: top 0.15s linear;
    }

    .ruler-tick {
      position: relative;
      padding-left: 18px;
      font-size: 10px;
      color: rgba(203, 213, 225, 0.72);
      font-variant-numeric: tabular-nums;
    }

    .ruler-tick::before {
      content: "";
      position: absolute;
      left: 4px;
      top: 50%;
      width: 8px;
      height: 1px;
      background: rgba(148, 163, 184, 0.5);
    }

    /* 3D projected callout pins */
    #callout-layer {
      position: fixed;
      inset: 0;
      pointer-events: none;
      overflow: hidden;
      z-index: 14;
    }

    .callout-pin {
      position: absolute;
      transform: translate(-50%, -100%);
      opacity: 0;
      transition: opacity 0.35s ease;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .callout-pin.visible {
      opacity: 1;
    }

    .callout-box {
      background: rgba(9, 15, 28, 0.86);
      border: 1px solid rgba(45, 212, 191, 0.65);
      border-radius: 8px;
      padding: 6px 11px;
      white-space: nowrap;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    }

    .callout-title {
      font-size: 12px;
      font-weight: 700;
      color: #f8fafc;
    }

    .callout-desc {
      font-size: 11px;
      color: #cbd5e1;
      margin-top: 2px;
    }

    .callout-stem {
      width: 1px;
      height: 26px;
      background: linear-gradient(to bottom, rgba(45, 212, 191, 0.9), rgba(45, 212, 191, 0.1));
    }

    .callout-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 10px rgba(45, 212, 191, 0.95);
    }

    /* Bottom cinema narrative console */
    #console {
      position: fixed;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%);
      width: min(860px, calc(100vw - 32px));
      background: var(--bg-panel);
      border: 1px solid var(--border-panel);
      backdrop-filter: blur(14px);
      border-radius: 16px;
      padding: 16px 20px 14px;
      z-index: 25;
      box-shadow: 0 14px 40px rgba(0, 0, 0, 0.48);
    }

    .narrative-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      gap: 12px;
    }

    #chapter-title {
      font-size: 17px;
      font-weight: 700;
      color: #f8fafc;
      letter-spacing: 0.02em;
    }

    #mode-badge {
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 999px;
      background: rgba(45, 212, 191, 0.16);
      border: 1px solid rgba(45, 212, 191, 0.45);
      color: var(--accent);
      white-space: nowrap;
    }

    #mode-badge.manual {
      background: rgba(245, 158, 11, 0.16);
      border-color: rgba(245, 158, 11, 0.5);
      color: #fbbf24;
    }

    #subtitle {
      font-size: 14px;
      line-height: 1.65;
      color: #e2e8f0;
      min-height: 46px;
      margin-bottom: 12px;
    }

    /* Segmented timeline */
    .timeline-row {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 6px;
      margin-bottom: 12px;
    }

    .seg-btn {
      background: transparent;
      border: none;
      cursor: pointer;
      text-align: left;
      padding: 0;
      color: var(--text-muted);
    }

    .seg-bar {
      height: 5px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.25);
      overflow: hidden;
      margin-bottom: 5px;
    }

    .seg-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #14b8a6, #38bdf8);
      border-radius: 999px;
      transition: width 0.08s linear;
    }

    .seg-label {
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: color 0.15s ease;
    }

    .seg-btn.active .seg-label,
    .seg-btn:hover .seg-label {
      color: #f8fafc;
      font-weight: 600;
    }

    .transport-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .transport-left, .transport-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ctrl-btn {
      background: rgba(30, 41, 59, 0.85);
      color: #f1f5f9;
      border: 1px solid rgba(148, 163, 184, 0.28);
      border-radius: 8px;
      padding: 7px 12px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease;
    }

    .ctrl-btn:hover {
      background: rgba(51, 65, 85, 0.95);
      border-color: rgba(148, 163, 184, 0.55);
    }

    .ctrl-btn.primary {
      background: #0f766e;
      border-color: #14b8a6;
      color: #ffffff;
      min-width: 96px;
    }

    .ctrl-btn.primary:hover {
      background: #0d9488;
    }

    #time-readout {
      font-size: 12px;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
      min-width: 84px;
      text-align: center;
    }

    #loading-overlay {
      position: fixed;
      inset: 0;
      background: #060b16;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 100;
      transition: opacity 0.45s ease;
    }

    #loading-overlay.hidden {
      opacity: 0;
      pointer-events: none;
    }

    .loader-ring {
      width: 44px;
      height: 44px;
      border: 3px solid rgba(45, 212, 191, 0.2);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      margin-bottom: 14px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loader-text {
      font-size: 14px;
      color: #cbd5e1;
      letter-spacing: 0.06em;
    }

    @media (max-width: 760px) {
      #spec-card, #alt-ruler { display: none; }
      .seg-label { display: none; }
      #subtitle { font-size: 13px; min-height: 54px; }
    }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
      }
    }
  </script>
</head>
<body>
  <div id="loading-overlay">
    <div class="loader-ring"></div>
    <div class="loader-text">正在建構台北 101 3D 建築與解說場景 ...</div>
  </div>

  <div id="canvas-container"></div>
  <div id="callout-layer"></div>

  <div id="topbar">
    <div class="brand-card">
      <div class="brand-tag">ARCHITECTURAL EXPLAINER</div>
      <div class="brand-title">台北 101 建築與工程解說</div>
      <div class="brand-sub">Taipei 101｜總高 508.2 m｜101 層摩天大樓</div>
    </div>

    <div class="top-actions">
      <button id="btn-voice" class="pill-btn active">台灣女聲旁白：開啟</button>
      <button id="btn-xray" class="pill-btn">X-Ray 透視</button>
      <button id="btn-fireworks" class="pill-btn">跨年煙火</button>
      <button id="btn-daynight" class="pill-btn">光影：自動</button>
      <button id="btn-free" class="pill-btn">自由探索</button>
    </div>
  </div>

  <aside id="spec-card">
    <div class="spec-header">
      <span id="spec-chapter-id" class="spec-chapter-id">CHAPTER 01</span>
      <span id="spec-altitude" class="spec-altitude">海拔焦點 250 m</span>
    </div>
    <div id="spec-metrics" class="spec-metrics"></div>
  </aside>

  <div id="alt-ruler" aria-hidden="true">
    <div class="ruler-track"></div>
    <div id="ruler-indicator" style="top: 50%;"></div>
    <div class="ruler-tick">508 m</div>
    <div class="ruler-tick">385 m</div>
    <div class="ruler-tick">250 m</div>
    <div class="ruler-tick">113 m</div>
    <div class="ruler-tick">0 m</div>
  </div>

  <section id="console">
    <div class="narrative-head">
      <div id="chapter-title">01｜台灣天際線地標：台北 101</div>
      <span id="mode-badge">自動導覽中</span>
    </div>
    <div id="subtitle"></div>

    <div id="timeline-row" class="timeline-row"></div>

    <div class="transport-row">
      <div class="transport-left">
        <button id="btn-play" class="ctrl-btn primary">暫停播放</button>
        <button id="btn-prev" class="ctrl-btn">上一章</button>
        <button id="btn-next" class="ctrl-btn">下一章</button>
        <button id="btn-restart" class="ctrl-btn">重頭播放</button>
      </div>
      <div class="transport-right">
        <span id="time-readout">00:00 / 01:26</span>
      </div>
    </div>
  </section>

  <script id="embedded-glb" type="application/octet-stream">__EMBEDDED_GLB_BASE64__</script>
  <script id="embedded-audio" type="application/json">__EMBEDDED_AUDIO_JSON__</script>

  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/addons/controls/OrbitControls.js";
    import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

    // -----------------------------------------------------------------------
    // 1. Storyboard Chapters (Total 86 seconds)
    // -----------------------------------------------------------------------
    const CHAPTERS = [
      {
        id: "CHAPTER 01",
        short: "01 地標總覽",
        title: "01｜台灣天際線地標：台北 101",
        duration: 12,
        theme: "dusk",
        xray: false,
        wireframe: false,
        wind: false,
        fireworks: false,
        scanY: null,
        altitudeLabel: "全景 0–508.2 m",
        focusY: 255,
        camStart: [290, 150, 320],
        camEnd: [210, 290, 310],
        targetStart: [0, 220, 0],
        targetEnd: [0, 265, 0],
        subtitle:
          "台北 101 位於台北信義計畫區，於 2004 年落成，總高度達 508.2 公尺，地上 101 層、地下 5 層，曾蟬聯世界第一高樓長達六年，是台灣最具代表性的建築地標。",
        metrics: [
          { label: "總高度", value: "508.2 m" },
          { label: "樓層數", value: "101F / B5" },
          { label: "落成年份", value: "2004 年" },
          { label: "建築師", value: "李祖原團隊" }
        ],
        callouts: [
          { pos: [0, 508, 0], title: "塔尖最高點 508.2 m", desc: "避雷針與航空警示燈" },
          { pos: [0, 250, 24], title: "8 節竹節主塔", desc: "26F 至 90F 辦公空間" }
        ]
      },
      {
        id: "CHAPTER 02",
        short: "02 基地裙樓",
        title: "02｜階梯式基地廣場與裙樓商場",
        duration: 11,
        theme: "day",
        xray: false,
        wireframe: false,
        wind: false,
        fireworks: false,
        scanY: 22,
        altitudeLabel: "1F–25F (0–113 m)",
        focusY: 45,
        camStart: [165, 48, 145],
        camEnd: [120, 72, -110],
        targetStart: [16, 36, 0],
        targetEnd: [10, 52, 0],
        subtitle:
          "建築底部由階梯式花崗岩廣場、東側 6 層購物中心裙樓，以及 1 至 25 層向上內收的梯形塔座組成，形如穩固寶鼎，為上方高聳塔身提供紮實的視覺與結構基礎。",
        metrics: [
          { label: "裙樓高度", value: "約 28 m" },
          { label: "梯形底座", value: "1F – 25F" },
          { label: "底座頂高", value: "113 m" },
          { label: "基地機能", value: "商場與金融" }
        ],
        callouts: [
          { pos: [42, 30, 0], title: "台北 101 購物中心", desc: "東側低樓層商業裙樓" },
          { pos: [0, 62, 28], title: "內縮梯形底座", desc: "1F 至 25F 穩固基座" }
        ]
      },
      {
        id: "CHAPTER 03",
        short: "03 古銅錢符碼",
        title: "03｜26 樓古銅錢與東方吉祥語彙",
        duration: 12,
        theme: "day",
        xray: false,
        wireframe: false,
        wind: false,
        fireworks: false,
        scanY: 110,
        altitudeLabel: "26F (109.5 m)",
        focusY: 110,
        camStart: [72, 118, 92],
        camEnd: [-38, 126, 98],
        targetStart: [0, 110, 16],
        targetEnd: [0, 112, 16],
        subtitle:
          "在底座與主塔交界的 26 樓四面立面，鑲嵌著直徑超過 10 公尺的巨型古銅錢，搭配各節轉角的祥雲「如意」裝飾，將中華文化中招財納福的象徵轉化為現代摩天建築語彙。",
        metrics: [
          { label: "裝飾位置", value: "26F 四面" },
          { label: "高度位置", value: "109.5 m" },
          { label: "古錢直徑", value: "約 10.8 m" },
          { label: "文化意象", value: "古錢與如意" }
        ],
        callouts: [
          { pos: [0, 109.5, 24], title: "巨型古銅錢裝飾", desc: "外圓內方・象徵金融繁榮" },
          { pos: [21, 114, 21], title: "如意雲紋轉角", desc: "融合傳統吉祥符號" }
        ]
      },
      {
        id: "CHAPTER 04",
        short: "04 竹節減風",
        title: "04｜8 節竹節塔身與 W 型鋸齒轉角",
        duration: 13,
        theme: "day",
        xray: false,
        wireframe: false,
        wind: true,
        fireworks: false,
        scanY: 250,
        altitudeLabel: "26F–90F (113–385 m)",
        focusY: 250,
        camStart: [125, 140, 125],
        camEnd: [135, 365, -95],
        targetStart: [0, 165, 0],
        targetEnd: [0, 330, 0],
        subtitle:
          "主塔由 8 個每節 8 層的倒梯形單元層層疊起，呼應「竹節高升」與華人文化「發」的吉祥數字；四角採 W 型雙重內縮鋸齒切角，經風洞實測可有效削減約 30% 至 40% 的高空渦流風壓。",
        metrics: [
          { label: "結構單元", value: "8 節 × 8 層" },
          { label: "外傾角度", value: "約 7°" },
          { label: "轉角造型", value: "W 型鋸齒" },
          { label: "風壓削減", value: "30% – 40%" }
        ],
        callouts: [
          { pos: [24, 215, 24], title: "W 型鋸齒切角", desc: "打散高空渦流、降低橫風振動" },
          { pos: [0, 315, 24], title: "8 節倒梯形竹節", desc: "每節 8 層・象徵節節高升" }
        ]
      },
      {
        id: "CHAPTER 05",
        short: "05 抗震巨柱",
        title: "05｜8 根外露巨柱與高強度抗震骨架",
        duration: 12,
        theme: "dusk",
        xray: false,
        wireframe: true,
        wind: false,
        fireworks: false,
        scanY: 200,
        altitudeLabel: "核心結構 (4–448 m)",
        focusY: 210,
        camStart: [110, 185, 110],
        camEnd: [-105, 275, 115],
        targetStart: [0, 195, 0],
        targetEnd: [0, 235, 0],
        subtitle:
          "面對台灣頻繁的地震與颱風，台北 101 採用外圍 8 根巨型鋼骨柱包覆 10,000 psi 高性能混凝土，並以每隔 8 層的巨型桁架將外柱與中央核心筒緊密連結，兼顧超高剛性與抗震韌性。",
        metrics: [
          { label: "外露巨柱", value: "8 根巨柱" },
          { label: "混凝土強度", value: "10,000 psi" },
          { label: "基樁數量", value: "380 支基樁" },
          { label: "入岩深度", value: "最深 80 m" }
        ],
        callouts: [
          { pos: [23, 240, 7], title: "外圍巨型柱 Mega-Column", desc: "鋼板箱型斷面灌注高強混凝土" },
          { pos: [-23, 180, 7], title: "巨型外伸桁架層", desc: "每 8 層串聯核心筒與外柱" }
        ]
      },
      {
        id: "CHAPTER 06",
        short: "06 風阻尼球",
        title: "06｜660 公噸黃金風阻尼球（TMD）",
        duration: 14,
        theme: "night",
        xray: true,
        wireframe: false,
        wind: true,
        fireworks: false,
        scanY: 382,
        altitudeLabel: "87F–92F (382 m)",
        focusY: 382,
        camStart: [72, 396, 72],
        camEnd: [-48, 386, 58],
        targetStart: [0, 382, 0],
        targetEnd: [0, 382, 0],
        subtitle:
          "懸吊於 87 至 92 樓中央的調諧質塊阻尼器，由 41 層實心鋼板焊接而成，直徑 5.5 公尺、重達 660 公噸。當強風吹襲塔頂時，阻尼球反向擺盪並由底部液壓器耗散能量，可降低高達 40% 的搖晃幅度。",
        metrics: [
          { label: "阻尼球重量", value: "660 公噸" },
          { label: "球體直徑", value: "5.5 公尺" },
          { label: "懸吊樓層", value: "87F – 92F" },
          { label: "減震效能", value: "最高 40%" }
        ],
        callouts: [
          { pos: [0, 382, 0], title: "660 公噸風阻尼球 TMD", desc: "41 層鋼板疊焊・8 條鋼索懸吊" }
        ]
      },
      {
        id: "CHAPTER 07",
        short: "07 觀景與煙火",
        title: "07｜高空觀景台、塔尖與跨年煙火",
        duration: 12,
        theme: "night",
        xray: false,
        wireframe: false,
        wind: false,
        fireworks: true,
        scanY: null,
        altitudeLabel: "89F–101F (385–508.2 m)",
        focusY: 420,
        camStart: [115, 445, 115],
        camEnd: [295, 235, 315],
        targetStart: [0, 445, 0],
        targetEnd: [0, 275, 0],
        subtitle:
          "登上 89 樓室內觀景台與 91 樓戶外平台，可 360 度俯瞰大台北盆地。每年跨年夜，台北 101 化身世界注目的立體煙火舞台，以萬發火光點亮台北夜空，向世界展現台灣的工程美學與城市活力。",
        metrics: [
          { label: "89F 觀景台", value: "382 m" },
          { label: "高速電梯", value: "60.6 km/h" },
          { label: "5F→89F", value: "僅需 37 秒" },
          { label: "綠建築認證", value: "LEED 白金" }
        ],
        callouts: [
          { pos: [0, 455, 0], title: "60 公尺避雷塔尖", desc: "總高 508.2 m 最高點" },
          { pos: [0, 392, 18], title: "89F–91F 觀景台", desc: "超高速電梯 37 秒直達" }
        ]
      }
    ];

    const AUDIO_DURATIONS = __CHAPTER_DURATIONS_JSON__;
    if (Array.isArray(AUDIO_DURATIONS) && AUDIO_DURATIONS.length === CHAPTERS.length) {
      CHAPTERS.forEach((c, i) => {
        c.duration = AUDIO_DURATIONS[i];
      });
    }

    const TOTAL_DURATION = CHAPTERS.reduce((acc, c) => acc + c.duration, 0);
    const CHAPTER_STARTS = [];
    {
      let acc = 0;
      for (const c of CHAPTERS) {
        CHAPTER_STARTS.push(acc);
        acc += c.duration;
      }
    }

    // -----------------------------------------------------------------------
    // 2. Three.js Scene Setup
    // -----------------------------------------------------------------------
    const container = document.getElementById("canvas-container");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x091324);
    scene.fog = new THREE.FogExp2(0x091324, 0.00055);

    const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 1, 3500);
    camera.position.set(290, 150, 320);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI * 0.495;
    controls.minDistance = 42;
    controls.maxDistance = 950;
    controls.target.set(0, 220, 0);

    // Lighting rig
    const hemiLight = new THREE.HemisphereLight(0x88b4e8, 0x1e293b, 0.9);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff1dc, 2.1);
    sunLight.position.set(260, 420, 220);
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x4ea8de, 0.75);
    fillLight.position.set(-240, 180, -210);
    scene.add(fillLight);

    const uplight = new THREE.PointLight(0x2dd4bf, 1.5, 420, 1.4);
    uplight.position.set(0, 60, 0);
    scene.add(uplight);

    // Ground & stylized Xinyi city skyline context
    const groundGeo = new THREE.CircleGeometry(1400, 64);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x0b1220,
      roughness: 0.92,
      metalness: 0.08
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.2;
    scene.add(ground);

    const gridHelper = new THREE.GridHelper(1200, 48, 0x1e3a5f, 0x122238);
    gridHelper.position.y = 0.05;
    scene.add(gridHelper);

    // Stylized surrounding buildings to emphasize 508.2 m scale
    const cityGroup = new THREE.Group();
    const cityMat = new THREE.MeshStandardMaterial({
      color: 0x152238,
      roughness: 0.75,
      metalness: 0.25,
      emissive: 0x0b1a2e,
      emissiveIntensity: 0.45
    });
    const citySeed = (n) => {
      const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
      return x - Math.floor(x);
    };
    for (let i = 0; i < 95; i++) {
      const angle = citySeed(i * 3 + 1) * Math.PI * 2;
      const dist = 125 + citySeed(i * 3 + 2) * 440;
      const w = 18 + citySeed(i * 5 + 3) * 34;
      const d = 18 + citySeed(i * 7 + 4) * 34;
      const h = 24 + Math.pow(citySeed(i * 11 + 5), 2.1) * 185;
      const bx = Math.cos(angle) * dist;
      const bz = Math.sin(angle) * dist;
      // Keep immediate east mall plaza clear
      if (bx > 10 && bx < 115 && Math.abs(bz) < 75) continue;
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), cityMat);
      mesh.position.set(bx, h * 0.5, bz);
      cityGroup.add(mesh);
    }
    scene.add(cityGroup);

    // Starfield for night/dusk
    const starCount = 900;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 900 + Math.random() * 900;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.45;
      starPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPositions[i * 3 + 1] = r * Math.cos(phi) + 80;
      starPositions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({ color: 0xcbd5e1, size: 2.2, transparent: true, opacity: 0.7 });
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // -----------------------------------------------------------------------
    // 3. Taipei 101 Model + Internal Tuned Mass Damper (87F-92F)
    // -----------------------------------------------------------------------
    const towerRoot = new THREE.Group();
    scene.add(towerRoot);

    const modelMaterials = [];
    let towerLoaded = false;

    // Internal Tuned Mass Damper (TMD) at y = 382 m
    const tmdPivot = new THREE.Group();
    tmdPivot.position.set(0, 398, 0); // Suspension anchor near 92F
    towerRoot.add(tmdPivot);

    const cableLen = 16;
    const sphereRadius = 4.6; // Slightly emphasized from 2.75 m for clear 3D visual legibility

    const goldMat = new THREE.MeshStandardMaterial({
      color: 0xf5b731,
      metalness: 0.86,
      roughness: 0.22,
      emissive: 0x6b4500,
      emissiveIntensity: 0.45
    });

    const tmdBall = new THREE.Mesh(new THREE.SphereGeometry(sphereRadius, 36, 28), goldMat);
    tmdBall.position.set(0, -cableLen, 0);
    tmdPivot.add(tmdBall);

    // Horizontal steel plate rings on TMD ball (representing 41 welded plates)
    const ringPlateMat = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      metalness: 0.9,
      roughness: 0.3
    });
    for (let k = -3; k <= 3; k++) {
      const yOff = k * 1.1;
      const r = Math.sqrt(Math.max(0.1, sphereRadius * sphereRadius - yOff * yOff)) + 0.08;
      const band = new THREE.Mesh(new THREE.TorusGeometry(r, 0.09, 8, 36), ringPlateMat);
      band.rotation.x = Math.PI / 2;
      band.position.set(0, -cableLen + yOff, 0);
      tmdPivot.add(band);
    }

    // 8 steel suspension cables
    const cableMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.85, roughness: 0.25 });
    for (let i = 0; i < 8; i++) {
      const ang = (i / 8) * Math.PI * 2;
      const cx = Math.cos(ang) * 2.1;
      const cz = Math.sin(ang) * 2.1;
      const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, cableLen, 8), cableMat);
      cable.position.set(cx, -cableLen * 0.5, cz);
      tmdPivot.add(cable);
    }

    // Hydraulic bumper ring below TMD
    const bumperRing = new THREE.Mesh(
      new THREE.TorusGeometry(7.5, 0.35, 12, 32),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.6 })
    );
    bumperRing.rotation.x = Math.PI / 2;
    bumperRing.position.set(0, 376, 0);
    towerRoot.add(bumperRing);

    const tmdLight = new THREE.PointLight(0xfbbf24, 3.5, 65, 1.5);
    tmdLight.position.set(0, 382, 0);
    towerRoot.add(tmdLight);

    // Highlight scan ring around tower
    const scanRingGeo = new THREE.RingGeometry(28, 32.5, 48);
    const scanRingMat = new THREE.MeshBasicMaterial({
      color: 0x2dd4bf,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.0
    });
    const scanRing = new THREE.Mesh(scanRingGeo, scanRingMat);
    scanRing.rotation.x = -Math.PI / 2;
    scanRing.position.y = 110;
    scene.add(scanRing);

    // -----------------------------------------------------------------------
    // 4. Wind Streamlines & Fireworks Particle Systems
    // -----------------------------------------------------------------------
    const WIND_COUNT = 260;
    const windPos = new Float32Array(WIND_COUNT * 3);
    const windSpeeds = new Float32Array(WIND_COUNT);
    for (let i = 0; i < WIND_COUNT; i++) {
      windPos[i * 3] = (Math.random() - 0.5) * 260;
      windPos[i * 3 + 1] = 120 + Math.random() * 310;
      windPos[i * 3 + 2] = (Math.random() - 0.5) * 140;
      windSpeeds[i] = 75 + Math.random() * 85;
    }
    const windGeo = new THREE.BufferGeometry();
    windGeo.setAttribute("position", new THREE.BufferAttribute(windPos, 3));
    const windMat = new THREE.PointsMaterial({
      color: 0x7dd3fc,
      size: 2.6,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const windParticles = new THREE.Points(windGeo, windMat);
    scene.add(windParticles);

    // Fireworks burst particles around the 8 bamboo modules
    const FW_COUNT = 900;
    const fwPositions = new Float32Array(FW_COUNT * 3);
    const fwColors = new Float32Array(FW_COUNT * 3);
    const fwVel = [];
    const fwLife = new Float32Array(FW_COUNT);
    const fwPalette = [
      new THREE.Color(0xfbbf24),
      new THREE.Color(0x2dd4bf),
      new THREE.Color(0xf43f5e),
      new THREE.Color(0x60a5fa),
      new THREE.Color(0xfef08a)
    ];

    function resetFireworkParticle(i) {
      const tier = Math.floor(Math.random() * 8);
      const baseY = 135 + tier * 34 + (Math.random() - 0.5) * 8;
      const ang = Math.random() * Math.PI * 2;
      const radius = 24;
      fwPositions[i * 3] = Math.cos(ang) * radius;
      fwPositions[i * 3 + 1] = baseY;
      fwPositions[i * 3 + 2] = Math.sin(ang) * radius;

      const speed = 28 + Math.random() * 58;
      const elev = (Math.random() - 0.22) * 0.9;
      fwVel[i] = new THREE.Vector3(
        Math.cos(ang) * speed * Math.cos(elev),
        speed * Math.sin(elev) + 12,
        Math.sin(ang) * speed * Math.cos(elev)
      );
      fwLife[i] = 0.6 + Math.random() * 1.4;

      const c = fwPalette[(tier + (i % fwPalette.length)) % fwPalette.length];
      fwColors[i * 3] = c.r;
      fwColors[i * 3 + 1] = c.g;
      fwColors[i * 3 + 2] = c.b;
    }

    for (let i = 0; i < FW_COUNT; i++) {
      resetFireworkParticle(i);
      fwLife[i] *= Math.random();
    }

    const fwGeo = new THREE.BufferGeometry();
    fwGeo.setAttribute("position", new THREE.BufferAttribute(fwPositions, 3));
    fwGeo.setAttribute("color", new THREE.BufferAttribute(fwColors, 3));
    const fwMat = new THREE.PointsMaterial({
      size: 4.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const fireworksPoints = new THREE.Points(fwGeo, fwMat);
    scene.add(fireworksPoints);

    // -----------------------------------------------------------------------
    // 5. Load Embedded GLB (with fallback to ./taipei_101.glb)
    // -----------------------------------------------------------------------
    const loader = new GLTFLoader();

    function onModelReady(gltf) {
      const model = gltf.scene;
      model.traverse((child) => {
        if (child.isMesh && child.material) {
          const mat = child.material.clone();
          mat.userData.origOpacity = mat.opacity ?? 1.0;
          mat.userData.origEmissive = mat.emissive ? mat.emissive.clone() : new THREE.Color(0x000000);
          mat.userData.origEmissiveIntensity = mat.emissiveIntensity ?? 1.0;
          mat.userData.name = mat.name || "";
          child.material = mat;
          modelMaterials.push(mat);
        }
      });
      towerRoot.add(model);
      towerLoaded = true;
      document.getElementById("loading-overlay").classList.add("hidden");
      applyChapterUI(0, true);
    }

    function loadEmbeddedGlb() {
      const el = document.getElementById("embedded-glb");
      const b64 = el ? el.textContent.trim() : "";
      if (b64 && !b64.startsWith("__EMBEDDED")) {
        const binStr = atob(b64);
        const bytes = new Uint8Array(binStr.length);
        for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
        loader.parse(bytes.buffer, "", onModelReady, (err) => {
          console.error("GLB parse error:", err);
        });
      } else {
        loader.load("./taipei_101.glb", onModelReady);
      }
    }
    loadEmbeddedGlb();

    // -----------------------------------------------------------------------
    // 6. Playback, Camera Choreography, Voiceover & Interactive Controls
    // -----------------------------------------------------------------------
    let isPlaying = true;
    let isManualOrbit = false;
    let globalTime = 0;
    let currentChapterIdx = 0;
    let voiceEnabled = true;
    let audioUnlocked = false;

    // Embedded Taiwanese female neural narration (zh-TW-HsiaoChenNeural)
    let embeddedAudioMap = {};
    try {
      const audioScript = document.getElementById("embedded-audio");
      const rawJson = audioScript ? audioScript.textContent.trim() : "";
      if (rawJson && !rawJson.startsWith("__EMBEDDED")) {
        embeddedAudioMap = JSON.parse(rawJson);
      }
    } catch (e) {
      console.warn("Embedded audio parse skipped:", e);
    }

    const narrationAudio = new Audio();
    narrationAudio.preload = "auto";
    let loadedAudioIdx = -1;

    function updateVoiceButtonLabel() {
      if (!voiceEnabled) {
        btnVoice.classList.remove("active");
        btnVoice.textContent = "台灣女聲旁白：關閉";
      } else if (!audioUnlocked && Object.keys(embeddedAudioMap).length > 0) {
        btnVoice.classList.add("active");
        btnVoice.textContent = "點擊啟用台灣女聲";
      } else {
        btnVoice.classList.add("active");
        btnVoice.textContent = "台灣女聲旁白：開啟";
      }
    }

    function stopNarration(resetPos = false) {
      narrationAudio.pause();
      if (resetPos) {
        narrationAudio.currentTime = 0;
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    }

    function pickTaiwanFemaleVoice() {
      if (!("speechSynthesis" in window)) return null;
      const voices = window.speechSynthesis.getVoices() || [];
      return (
        voices.find((v) => /hsiaochen|hsiaoyu/i.test(v.name)) ||
        voices.find((v) => v.lang === "zh-TW" && /google|female|女|yating|hanhan/i.test(v.name)) ||
        voices.find((v) => v.lang === "zh-TW") ||
        null
      );
    }

    function playChapterNarration(idx, offsetSec = 0) {
      if (!voiceEnabled || !isPlaying) {
        stopNarration(false);
        return;
      }

      const dataUrl = embeddedAudioMap[String(idx)];
      if (dataUrl) {
        if (loadedAudioIdx !== idx) {
          narrationAudio.src = dataUrl;
          loadedAudioIdx = idx;
        }
        try {
          narrationAudio.currentTime = Math.max(0, offsetSec);
        } catch (_) {}

        const playPromise = narrationAudio.play();
        if (playPromise && typeof playPromise.then === "function") {
          playPromise
            .then(() => {
              audioUnlocked = true;
              updateVoiceButtonLabel();
            })
            .catch(() => {
              audioUnlocked = false;
              updateVoiceButtonLabel();
            });
        }
        return;
      }

      // Fallback to Web Speech API (prefer zh-TW female voice)
      if (!("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(CHAPTERS[idx].subtitle);
      utter.lang = "zh-TW";
      const twVoice = pickTaiwanFemaleVoice();
      if (twVoice) utter.voice = twVoice;
      utter.rate = 0.98;
      utter.pitch = 1.02;
      window.speechSynthesis.speak(utter);
    }

    // Unlock audio smoothly on first user interaction if browser blocked autoplay
    function tryUnlockAudioOnce() {
      if (audioUnlocked || !voiceEnabled || !isPlaying) return;
      const localSec = Math.max(0, globalTime - CHAPTER_STARTS[currentChapterIdx]);
      playChapterNarration(currentChapterIdx, localSec);
    }
    window.addEventListener("pointerdown", tryUnlockAudioOnce, { passive: true });
    window.addEventListener("keydown", tryUnlockAudioOnce, { passive: true });

    // Manual overrides (null = follow chapter storyboard)
    let overrideXray = null;
    let overrideFireworks = null;
    let overrideTheme = null; // null | "day" | "dusk" | "night"

    // DOM refs
    const elTitle = document.getElementById("chapter-title");
    const elSubtitle = document.getElementById("subtitle");
    const elSpecId = document.getElementById("spec-chapter-id");
    const elSpecAlt = document.getElementById("spec-altitude");
    const elSpecMetrics = document.getElementById("spec-metrics");
    const elModeBadge = document.getElementById("mode-badge");
    const elTimeReadout = document.getElementById("time-readout");
    const elRulerInd = document.getElementById("ruler-indicator");
    const elCalloutLayer = document.getElementById("callout-layer");
    const btnPlay = document.getElementById("btn-play");
    const btnVoice = document.getElementById("btn-voice");
    const btnXray = document.getElementById("btn-xray");
    const btnFireworks = document.getElementById("btn-fireworks");
    const btnDayNight = document.getElementById("btn-daynight");
    const btnFree = document.getElementById("btn-free");

    // Build segmented timeline UI
    const timelineRow = document.getElementById("timeline-row");
    const segButtons = [];
    const segFills = [];
    CHAPTERS.forEach((ch, idx) => {
      const btn = document.createElement("button");
      btn.className = "seg-btn";
      btn.innerHTML = `
        <div class="seg-bar"><div class="seg-fill"></div></div>
        <div class="seg-label">${ch.short}</div>
      `;
      btn.addEventListener("click", () => jumpToChapter(idx));
      timelineRow.appendChild(btn);
      segButtons.push(btn);
      segFills.push(btn.querySelector(".seg-fill"));
    });

    // Active 3D callout DOM nodes
    let activeCalloutNodes = [];

    function rebuildCallouts(chapter) {
      elCalloutLayer.innerHTML = "";
      activeCalloutNodes = (chapter.callouts || []).map((c) => {
        const pin = document.createElement("div");
        pin.className = "callout-pin visible";
        pin.innerHTML = `
          <div class="callout-box">
            <div class="callout-title">${c.title}</div>
            <div class="callout-desc">${c.desc}</div>
          </div>
          <div class="callout-stem"></div>
          <div class="callout-dot"></div>
        `;
        elCalloutLayer.appendChild(pin);
        return { el: pin, worldPos: new THREE.Vector3(...c.pos) };
      });
    }

    function applyChapterUI(idx, shouldSpeak = true) {
      currentChapterIdx = idx;
      const ch = CHAPTERS[idx];
      elTitle.textContent = ch.title;
      elSubtitle.textContent = ch.subtitle;
      elSpecId.textContent = ch.id;
      elSpecAlt.textContent = ch.altitudeLabel;

      elSpecMetrics.innerHTML = ch.metrics
        .map(
          (m) => `
          <div class="metric-box">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
          </div>`
        )
        .join("");

      segButtons.forEach((b, i) => b.classList.toggle("active", i === idx));
      rebuildCallouts(ch);

      const pct = 100 - Math.min(100, Math.max(0, (ch.focusY / 508.25) * 100));
      elRulerInd.style.top = `${pct}%`;

      if (shouldSpeak) {
        const localSec = Math.max(0, globalTime - CHAPTER_STARTS[idx]);
        playChapterNarration(idx, localSec);
      }
    }

    function jumpToChapter(idx) {
      const clamped = Math.max(0, Math.min(CHAPTERS.length - 1, idx));
      globalTime = CHAPTER_STARTS[clamped];
      isManualOrbit = false;
      updateModeBadge();
      applyChapterUI(clamped, true);
    }

    function updateModeBadge() {
      if (isManualOrbit) {
        elModeBadge.textContent = "自由探索模式";
        elModeBadge.classList.add("manual");
        btnFree.classList.add("active");
        btnFree.textContent = "返回導覽";
      } else {
        elModeBadge.textContent = isPlaying ? "自動導覽中" : "已暫停";
        elModeBadge.classList.remove("manual");
        btnFree.classList.remove("active");
        btnFree.textContent = "自由探索";
      }
      btnPlay.textContent = isPlaying ? "暫停播放" : "繼續播放";
    }

    // User pointer drag switches smoothly to manual orbit
    controls.addEventListener("start", () => {
      if (!isManualOrbit) {
        isManualOrbit = true;
        updateModeBadge();
      }
    });

    btnPlay.addEventListener("click", () => {
      isPlaying = !isPlaying;
      if (isPlaying && isManualOrbit) isManualOrbit = false;
      if (isPlaying && globalTime >= TOTAL_DURATION - 0.1) {
        globalTime = 0;
        applyChapterUI(0, true);
      } else if (!isPlaying) {
        stopNarration(false);
      } else if (isPlaying) {
        const localSec = Math.max(0, globalTime - CHAPTER_STARTS[currentChapterIdx]);
        playChapterNarration(currentChapterIdx, localSec);
      }
      updateModeBadge();
    });

    document.getElementById("btn-prev").addEventListener("click", () => {
      jumpToChapter(currentChapterIdx - 1);
    });

    document.getElementById("btn-next").addEventListener("click", () => {
      jumpToChapter(currentChapterIdx + 1);
    });

    document.getElementById("btn-restart").addEventListener("click", () => {
      isPlaying = true;
      jumpToChapter(0);
      updateModeBadge();
    });

    btnFree.addEventListener("click", () => {
      isManualOrbit = !isManualOrbit;
      updateModeBadge();
    });

    btnVoice.addEventListener("click", () => {
      if (voiceEnabled && !audioUnlocked && Object.keys(embeddedAudioMap).length > 0) {
        // First click when autoplay was blocked: unlock & play instead of turning off
        const localSec = Math.max(0, globalTime - CHAPTER_STARTS[currentChapterIdx]);
        playChapterNarration(currentChapterIdx, localSec);
        return;
      }
      voiceEnabled = !voiceEnabled;
      updateVoiceButtonLabel();
      if (voiceEnabled) {
        const localSec = Math.max(0, globalTime - CHAPTER_STARTS[currentChapterIdx]);
        playChapterNarration(currentChapterIdx, localSec);
      } else {
        stopNarration(false);
      }
    });

    btnXray.addEventListener("click", () => {
      overrideXray = overrideXray === null ? true : !overrideXray;
      btnXray.classList.toggle("active", overrideXray);
    });

    btnFireworks.addEventListener("click", () => {
      overrideFireworks = overrideFireworks === null ? true : !overrideFireworks;
      btnFireworks.classList.toggle("active", overrideFireworks);
    });

    const themeCycle = [null, "day", "dusk", "night"];
    const themeNames = { null: "自動", day: "日間", dusk: "黃昏", night: "夜景" };
    let themeCycleIdx = 0;
    btnDayNight.addEventListener("click", () => {
      themeCycleIdx = (themeCycleIdx + 1) % themeCycle.length;
      overrideTheme = themeCycle[themeCycleIdx];
      btnDayNight.textContent = `光影：${themeNames[String(overrideTheme)]}`;
      btnDayNight.classList.toggle("active", overrideTheme !== null);
    });

    window.addEventListener("keydown", (e) => {
      if (e.code === "Space") {
        e.preventDefault();
        btnPlay.click();
      } else if (e.code === "ArrowRight") {
        jumpToChapter(currentChapterIdx + 1);
      } else if (e.code === "ArrowLeft") {
        jumpToChapter(currentChapterIdx - 1);
      } else if (e.key.toLowerCase() === "m") {
        btnVoice.click();
      }
    });

    // -----------------------------------------------------------------------
    // 7. Environment Theme & Animation Loop
    // -----------------------------------------------------------------------
    const THEMES = {
      day: {
        bg: new THREE.Color(0x9ec5e8),
        fog: new THREE.Color(0xb7d4ed),
        sunColor: new THREE.Color(0xfff9ee),
        sunIntensity: 2.5,
        hemiIntensity: 1.25,
        starOpacity: 0.0,
        cityEmissive: 0.08
      },
      dusk: {
        bg: new THREE.Color(0x1b2845),
        fog: new THREE.Color(0x273654),
        sunColor: new THREE.Color(0xffa96b),
        sunIntensity: 1.9,
        hemiIntensity: 0.85,
        starOpacity: 0.35,
        cityEmissive: 0.32
      },
      night: {
        bg: new THREE.Color(0x060d1c),
        fog: new THREE.Color(0x091529),
        sunColor: new THREE.Color(0x8ec5ff),
        sunIntensity: 1.15,
        hemiIntensity: 0.55,
        starOpacity: 0.88,
        cityEmissive: 0.58
      }
    };

    const smoothCamPos = new THREE.Vector3(290, 150, 320);
    const smoothTarget = new THREE.Vector3(0, 220, 0);
    const desiredCamPos = new THREE.Vector3();
    const desiredTarget = new THREE.Vector3();

    function formatTime(sec) {
      const s = Math.max(0, Math.floor(sec));
      const mm = String(Math.floor(s / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      return `${mm}:${ss}`;
    }

    function easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function getChapterAtTime(t) {
      for (let i = CHAPTERS.length - 1; i >= 0; i--) {
        if (t >= CHAPTER_STARTS[i]) {
          const local = Math.min(1, Math.max(0, (t - CHAPTER_STARTS[i]) / CHAPTERS[i].duration));
          return { idx: i, local };
        }
      }
      return { idx: 0, local: 0 };
    }

    const clock = new THREE.Clock();

    function animate() {
      requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      const elapsed = clock.elapsedTime;

      if (isPlaying && towerLoaded) {
        globalTime += dt;
        if (globalTime >= TOTAL_DURATION) {
          globalTime = 0; // Loop smoothly
        }
      }

      const { idx, local } = getChapterAtTime(globalTime);
      if (idx !== currentChapterIdx) {
        applyChapterUI(idx, true);
      }

      const ch = CHAPTERS[idx];

      // Update timeline bars & readout
      for (let i = 0; i < CHAPTERS.length; i++) {
        if (i < idx) segFills[i].style.width = "100%";
        else if (i > idx) segFills[i].style.width = "0%";
        else segFills[i].style.width = `${(local * 100).toFixed(1)}%`;
      }
      elTimeReadout.textContent = `${formatTime(globalTime)} / ${formatTime(TOTAL_DURATION)}`;

      // Camera choreography
      if (!isManualOrbit) {
        const e = easeInOutCubic(local);
        desiredCamPos.set(
          THREE.MathUtils.lerp(ch.camStart[0], ch.camEnd[0], e),
          THREE.MathUtils.lerp(ch.camStart[1], ch.camEnd[1], e),
          THREE.MathUtils.lerp(ch.camStart[2], ch.camEnd[2], e)
        );
        desiredTarget.set(
          THREE.MathUtils.lerp(ch.targetStart[0], ch.targetEnd[0], e),
          THREE.MathUtils.lerp(ch.targetStart[1], ch.targetEnd[1], e),
          THREE.MathUtils.lerp(ch.targetStart[2], ch.targetEnd[2], e)
        );
        const lerpRate = 1 - Math.exp(-3.4 * dt);
        camera.position.lerp(desiredCamPos, lerpRate);
        controls.target.lerp(desiredTarget, lerpRate);
      }
      controls.update();

      // Environment theme interpolation
      const activeThemeKey = overrideTheme || ch.theme;
      const targetTheme = THEMES[activeThemeKey];
      const themeRate = 1 - Math.exp(-2.2 * dt);
      scene.background.lerp(targetTheme.bg, themeRate);
      scene.fog.color.lerp(targetTheme.fog, themeRate);
      sunLight.color.lerp(targetTheme.sunColor, themeRate);
      sunLight.intensity = THREE.MathUtils.lerp(sunLight.intensity, targetTheme.sunIntensity, themeRate);
      hemiLight.intensity = THREE.MathUtils.lerp(hemiLight.intensity, targetTheme.hemiIntensity, themeRate);
      starMat.opacity = THREE.MathUtils.lerp(starMat.opacity, targetTheme.starOpacity, themeRate);
      cityMat.emissiveIntensity = THREE.MathUtils.lerp(cityMat.emissiveIntensity, targetTheme.cityEmissive, themeRate);

      // X-Ray & wireframe structural material transitions
      const activeXray = overrideXray !== null ? overrideXray : ch.xray;
      const activeWire = ch.wireframe && !activeXray;

      for (const mat of modelMaterials) {
        const isGlassOrFrame = mat.userData.name === "glass_curtain" || mat.userData.name === "aluminum_frame";
        const targetOpacity = activeXray ? (isGlassOrFrame ? 0.14 : 0.32) : 1.0;
        mat.transparent = targetOpacity < 0.99;
        mat.opacity = THREE.MathUtils.lerp(mat.opacity, targetOpacity, 1 - Math.exp(-5 * dt));
        mat.depthWrite = !mat.transparent;
        mat.wireframe = activeWire && mat.userData.name !== "mega_column";

        // Highlight mega-columns during Chapter 05
        if (ch.wireframe && mat.userData.name === "mega_column") {
          mat.emissive.setHex(0x14b8a6);
          mat.emissiveIntensity = 0.65;
        } else if (activeThemeKey === "night" && mat.userData.name === "glass_curtain") {
          mat.emissive.setHex(0x0c4a6e);
          mat.emissiveIntensity = 0.48;
        } else {
          mat.emissive.copy(mat.userData.origEmissive);
          mat.emissiveIntensity = mat.userData.origEmissiveIntensity;
        }
      }

      // TMD counter-swing physics visualization
      const swingAmp = activeXray ? 0.24 : 0.05;
      tmdPivot.rotation.z = Math.sin(elapsed * 2.2) * swingAmp;
      tmdPivot.rotation.x = Math.cos(elapsed * 1.4) * (swingAmp * 0.35);
      tmdLight.intensity = activeXray ? 4.5 : 0.6;

      // Scan highlight ring
      if (ch.scanY !== null) {
        scanRing.position.y = THREE.MathUtils.lerp(scanRing.position.y, ch.scanY + Math.sin(elapsed * 2.5) * 4, 0.12);
        scanRingMat.opacity = THREE.MathUtils.lerp(scanRingMat.opacity, 0.55, 0.1);
        const s = 1 + Math.sin(elapsed * 3.0) * 0.05;
        scanRing.scale.set(s, s, 1);
      } else {
        scanRingMat.opacity = THREE.MathUtils.lerp(scanRingMat.opacity, 0.0, 0.1);
      }

      // Wind streamlines
      const showWind = ch.wind || activeXray;
      windMat.opacity = THREE.MathUtils.lerp(windMat.opacity, showWind ? 0.72 : 0.0, 0.08);
      if (windMat.opacity > 0.02) {
        const arr = windGeo.attributes.position.array;
        for (let i = 0; i < WIND_COUNT; i++) {
          arr[i * 3] += windSpeeds[i] * dt;
          if (arr[i * 3] > 130) arr[i * 3] = -130;
        }
        windGeo.attributes.position.needsUpdate = true;
      }

      // Fireworks update
      const showFw = overrideFireworks !== null ? overrideFireworks : ch.fireworks;
      fwMat.opacity = THREE.MathUtils.lerp(fwMat.opacity, showFw ? 0.95 : 0.0, 0.08);
      if (fwMat.opacity > 0.02) {
        const posArr = fwGeo.attributes.position.array;
        for (let i = 0; i < FW_COUNT; i++) {
          fwLife[i] -= dt;
          if (fwLife[i] <= 0) {
            resetFireworkParticle(i);
          } else {
            fwVel[i].y -= 26 * dt; // Gravity
            posArr[i * 3] += fwVel[i].x * dt;
            posArr[i * 3 + 1] += fwVel[i].y * dt;
            posArr[i * 3 + 2] += fwVel[i].z * dt;
          }
        }
        fwGeo.attributes.position.needsUpdate = true;
        fwGeo.attributes.color.needsUpdate = true;
      }

      // Project 3D callout labels into 2D screen space
      const w = window.innerWidth;
      const h = window.innerHeight;
      for (const item of activeCalloutNodes) {
        const proj = item.worldPos.clone().project(camera);
        if (proj.z > 1 || proj.z < -1) {
          item.el.classList.remove("visible");
          continue;
        }
        const sx = (proj.x * 0.5 + 0.5) * w;
        const sy = (-proj.y * 0.5 + 0.5) * h;
        const inBounds = sx > 60 && sx < w - 60 && sy > 90 && sy < h - 190;
        item.el.classList.toggle("visible", inBounds);
        item.el.style.left = `${sx}px`;
        item.el.style.top = `${sy}px`;
      }

      renderer.render(scene, camera);
    }

    animate();

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  </script>
</body>
</html>
"""


def main() -> None:
    if not GLB_PATH.exists():
        raise FileNotFoundError(f"找不到模型檔案：{GLB_PATH}")

    glb_bytes = GLB_PATH.read_bytes()
    b64_str = base64.b64encode(glb_bytes).decode("ascii")

    audio_map = {}
    durations = []
    manifest_path = NARRATION_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for idx, item in enumerate(manifest):
            mp3_file = ROOT / item["file"]
            if mp3_file.exists():
                mp3_b64 = base64.b64encode(mp3_file.read_bytes()).decode("ascii")
                audio_map[str(idx)] = f"data:audio/mpeg;base64,{mp3_b64}"
                durations.append(round(float(item["duration"]) + 1.8, 1))

    html = HTML_TEMPLATE.replace("__EMBEDDED_GLB_BASE64__", b64_str)
    html = html.replace("__EMBEDDED_AUDIO_JSON__", json.dumps(audio_map, ensure_ascii=False))
    html = html.replace("__CHAPTER_DURATIONS_JSON__", json.dumps(durations))
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT_PATH}（大小：{OUT_PATH.stat().st_size:,} bytes，內嵌 {len(audio_map)} 段語音）")


if __name__ == "__main__":
    main()
