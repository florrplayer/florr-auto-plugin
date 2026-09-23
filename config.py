# -*- coding: utf-8 -*-
"""交互配置: 启动弹窗让玩家选 全程攻/防/不弄 + 能秒的怪等级; 存档后只问要不要更新"""
import json
import os
import tkinter as tk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULTS = {"mode": "defense", "kill_rank": "M", "version": 1}

MODE_NAMES = {"attack": "全程攻击", "defense": "全程防御", "none": "不弄(手动)"}
RANK_NAMES = {"M": "只打M(青)", "M+L": "M+传奇(红)", "none": "纯巡逻不打"}


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {**DEFAULTS, **cfg}
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
    ans = _ask("检测到已有设置：\n  模式：%s\n  打怪：%s\n\n要不要更新？" % (mode, rank),
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
    r = _ask("你可以秒（<3秒）哪个等级的怪？",
             [("M", "只打 M 怪（青色）"),
              ("M+L", "M + 传奇（红色）"),
              ("none", "纯巡逻不打怪")], "florr 挂机设置 ②/②")
    if r is None:
        r = "M"
    return {"mode": m, "kill_rank": r, "version": 1}
