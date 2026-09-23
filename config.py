# -*- coding: utf-8 -*-
"""交互配置: 启动弹窗让玩家选 全程攻/防/不弄 + 能秒的怪等级; 存档后只问要不要更新"""
import json
import os
import tkinter as tk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULTS = {"mode": "defense", "kill_rank": "mythic", "heal_slot": 0, "version": 3}

MODE_NAMES = {"attack": "全程攻击", "defense": "全程防御", "none": "不弄(手动)"}
RANK_ORDER = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]
RANK_NAMES = {"common": "普通(绿)", "unusual": "罕见(黄)", "rare": "稀有(蓝)", "epic": "史诗(紫)", "legendary": "传奇(红)", "mythic": "神话M(青)", "ultra": "究极U(粉)"}
HEAL_NAMES = {0: "不用(没带回血)", 1: "副槽1", 2: "副槽2", 3: "副槽3", 4: "副槽4", 5: "副槽5", 6: "副槽6", 7: "副槽7", 8: "副槽8", 9: "副槽9"}
# 旧配置兼容(1.x: M=只打神话, M+L=神话+传奇, none=纯巡逻)
RANK_LEGACY = {"M": "mythic", "M+L": "legendary", "none": "none"}


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg2 = {**DEFAULTS, **cfg}
        if cfg2["kill_rank"] in RANK_LEGACY:
            cfg2["kill_rank"] = RANK_LEGACY[cfg2["kill_rank"]]
        return cfg2
    except Exception:
        return None


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _ask(prompt, options, title):
    """弹窗: 显示 prompt + 按钮, 返回选中的 key(关窗口/异常返回 None)"""
    result = {"v": None}
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    tk.Label(root, text=prompt, font=("Microsoft YaHei UI", 12),
             padx=24, pady=14, justify="left").pack()
    for key, label in options:
        tk.Button(root, text=label, font=("Microsoft YaHei UI", 11), width=22,
                  command=lambda k=key: (result.update(v=k), root.destroy())[1]
                  ).pack(pady=4, padx=24)
    root.eval("tk::PlaceWindow . center")
    try:
        root.mainloop()
    except Exception:
        pass
    return result["v"]


def ask_update(cfg):
    """有存档时调用: 只问要不要更新(否→False 用旧设置)"""
    mode = MODE_NAMES.get(cfg.get("mode", "defense"), "?")
    rank = RANK_NAMES.get(cfg.get("kill_rank", "M"), "?")
    heal = HEAL_NAMES.get(cfg.get("heal_slot", 0), "?")
    ans = _ask("检测到已有设置：\n  模式：%s\n  打怪：%s\n  回血槽：%s\n\n要不要更新？" % (mode, rank, heal),
               [("yes", "更新设置"), ("no", "用旧设置继续")], "florr 挂机设置")
    return ans == "yes"


def ask_config():
    """首次/更新时调用: 依次问两个问题"""
    m = _ask("你想全程攻击还是防御还是不弄？",
             [("attack", "全程攻击（按空格发射花瓣）"),
              ("defense", "全程防御（按住右键，花瓣绕身转）"),
              ("none", "不弄（纯手动操作）")], "florr 挂机设置 ①/②")
    if m is None:
        m = "defense"
    r = _ask("你可以秒（<3秒）哪个等级的怪？\\n（=这级自动追贴脸打，更高避开，更低不管）",
             [(k, RANK_NAMES[k]) for k in RANK_ORDER], "florr 挂机设置 ②/②")
    if r is None:
        r = "mythic"
    hs = _ask("血量<10%时，切哪个副槽的回血花瓣（玫瑰/叶子）？\n（数字键把副槽该位切到主槽，恢复后自动切回）",
              [(str(i), HEAL_NAMES[i]) for i in range(1, 6)] + [("0", "不用(没带回血)")],
              "florr 挂机设置 ③/③")
    if hs is None:
        hs = "0"
    return {"mode": m, "kill_rank": r, "heal_slot": int(hs), "version": 3}
