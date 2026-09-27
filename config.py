# -*- coding: utf-8 -*-
"""交互配置: 启动弹窗让玩家选 全程攻/防/不弄 + 能秒的怪等级; 存档后只问要不要更新"""
import json
import os
import tkinter as tk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULTS = {"mode": "defense", "kill_rank": "mythic", "heal_slots": [], "patrol_points": [], "patrol_points_map": "", "region": "", "region_map": "", "efficiency": False, "leech": False, "heal_type": "rose", "version": 9}

MODE_NAMES = {"attack": "全程攻击", "defense": "全程防御", "none": "不弄(手动)"}
RANK_ORDER = ["common", "unusual", "rare", "epic", "legendary", "mythic", "ultra"]
RANK_NAMES = {"common": "普通(绿)", "unusual": "罕见(黄)", "rare": "稀有(蓝)", "epic": "史诗(紫)", "legendary": "传奇(红)", "mythic": "神话M(青)", "ultra": "究极U(粉)"}
HEAL_NAMES = {1: "副槽1", 2: "副槽2", 3: "副槽3", 4: "副槽4", 5: "副槽5", 6: "副槽6", 7: "副槽7", 8: "副槽8", 9: "副槽9", 10: "副槽10(0键)"}
HEAL_TYPE_NAMES = {"rose": "玫瑰Rose(爆发救急)", "dahlia": "大丽花Dahlia(稳定小回血)",
                   "yucca": "丝兰Yucca(防御时回血)", "starfish": "海星Starfish(被动回血)",
                   "leaf": "叶子Leaf(过渡用)"}
# 旧配置兼容(1.x: M=只打神话, M+L=神话+传奇, none=纯巡逻)
RANK_LEGACY = {"M": "mythic", "M+L": "legendary", "none": "none"}



# ===== 刷怪区域系统 =====
# 每图区域: (key, 显示名, 推荐秒杀档(kill_rank自动匹配用), 中心百分比(x,y) [地图像素=百分比x300], 巡逻半径百分比)
# ⚠️ 坐标为初版估算(依据研究手册分区描述)，实测位置不对时截图/报坐标给我精调；
#    也可在"要不要重新设置巡逻点"时选"重新设置"手动点选校准。
REGION_TABLE = {
    "garden": [
        ("ladybug", "出生点/瓢虫区（绿黄怪，新手）", ("common", "unusual"), (0.50, 0.78), 0.10),
        ("bee", "蜜蜂区（蓝紫怪）", ("rare", "epic"), (0.62, 0.58), 0.10),
        ("mini_spiral", "Mini Spiral（Mythic区）", ("legendary", "mythic"), (0.42, 0.35), 0.08),
        ("spiral", "Spiral（最深Ultra区，Super集中）", ("ultra",), (0.28, 0.22), 0.08),
    ],
    "desert": [
        ("entry", "入口区（绿→蓝怪，效率≈花园10倍）", ("common", "unusual", "rare"), (0.68, 0.62), 0.12),
        ("ss", "ss区（Legendary沙尘暴）", ("legendary",), (0.32, 0.55), 0.08),
        ("tunnel", "Tunnel（Mythic）", ("mythic",), (0.42, 0.25), 0.08),
        ("box", "Box（Ultra区，Super集中）", ("ultra",), (0.85, 0.15), 0.08),
    ],
    "anthell": [
        ("normal", "常规区（普通罕见）", ("common", "unusual"), (0.55, 0.70), 0.10),
        ("secret", "机密区（史诗传奇，密道左走）", ("epic", "legendary"), (0.35, 0.45), 0.08),
        ("top_secret", "绝密区（传奇+，概率刷Super）", ("mythic", "ultra"), (0.20, 0.30), 0.08),
    ],
    "ocean": [
        ("o1_3", "浅水区O1-3（蓝紫怪）", ("common", "unusual", "rare"), (0.50, 0.75), 0.10),
        ("o4_5", "中部O4-5（螃蟹王国，紫红怪）", ("epic", "legendary"), (0.55, 0.50), 0.08),
        ("o6_9", "深水区O6-9（水蛭/水母/海星，青粉怪）", ("mythic", "ultra"), (0.60, 0.20), 0.10),
    ],
    "jungle": [
        ("entry", "入口区（绿黄怪）", ("common", "unusual"), (0.50, 0.75), 0.10),
        ("deep", "丛林深处（紫红青怪，金叶虫出没）", ("legendary", "mythic", "ultra"), (0.45, 0.35), 0.10),
    ],
    "sewers": [
        ("entry", "入口区（绿黄怪）", ("common", "unusual"), (0.55, 0.72), 0.10),
        ("garbage", "垃圾袋区（传奇神话，S花瓣主刷）", ("legendary", "mythic"), (0.40, 0.45), 0.08),
        ("box", "Box（Ultra区，Super集中）", ("ultra",), (0.75, 0.15), 0.08),
    ],
    "factory": [
        ("mecha", "左上Mecha区（史诗传奇神话）", ("epic", "legendary", "mythic"), (0.15, 0.15), 0.10),
        ("center", "中央区（全档混刷）", ("rare", "epic"), (0.50, 0.50), 0.10),
    ],
    "crystal_room": [
        ("safe", "水晶室（无战斗怪，安全区）", ("none",), (0.50, 0.50), 0.20),
    ],
    "training_grounds": [
        ("train", "训练场（新手教程）", ("common",), (0.50, 0.50), 0.20),
    ],
    "hel": [
        ("pvp", "地狱（PvP向，挂机别去）", ("ultra",), (0.50, 0.50), 0.10),
    ],
}

# 秒杀档 -> 推荐区域名映射(自动模式): 每图按 REGION_TABLE 的推荐档匹配, 无匹配回退第一个
RANK_LEVEL = {"common": 0, "unusual": 1, "rare": 2, "epic": 3, "legendary": 4, "mythic": 5, "ultra": 6, "none": 99}


def region_options(map_name):
    """弹窗选项: (key, label)；第一个为自动(按秒杀等级推荐)"""
    opts = [("auto", "自动（按秒杀等级推荐刷怪区）")]
    for key, label, _, _, _ in REGION_TABLE.get(map_name, []):
        opts.append((key, label))
    return opts


def pick_region(map_name, kill_rank):
    """自动模式: 按秒杀等级匹配区域 key；无匹配回退第一个"""
    rows = REGION_TABLE.get(map_name, [])
    if not rows:
        return None
    lv = RANK_LEVEL.get(kill_rank, 99)
    # 找推荐档包含该等级的最近区域
    best, best_d = rows[0][0], 10 ** 9
    for key, _, ranks, _, _ in rows:
        for r in ranks:
            d = abs(RANK_LEVEL.get(r, 99) - lv)
            if d < best_d:
                best, best_d = key, d
    return best


def region_patrol_points(map_name, region_key, kill_rank):
    """生成区域信息: 区域圆(中心+半径)。返回 (区域名, 锚点列表, 区域圆(cx,cy,r))
    巡逻时在区域内随机取点(随机游走), 锚点仅供地图窗口显示"""
    rows = REGION_TABLE.get(map_name, [])
    key = region_key
    if key == "auto":
        key = pick_region(map_name, kill_rank)
    label = "自动(按秒杀等级)"
    cx, cy, radius = 0.5, 0.5, 0.10
    for k, lb, _, (px, py), pr in rows:
        if k == key:
            label, cx, cy, radius = lb, px, py, pr
            break
    S = 300  # 地图统一 300x300
    cxp, cyp = int(cx * S), int(cy * S)
    rp = max(6, int(radius * S))
    pts = [(cxp, cyp), (cxp + rp // 2, cyp), (cxp - rp // 2, cyp),
           (cxp, cyp + rp // 2), (cxp, cyp - rp // 2)]
    pts = [(min(295, max(2, x)), min(295, max(2, y))) for x, y in pts]
    return label, pts, (cxp, cyp, rp)


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg2 = {**DEFAULTS, **cfg}
        if cfg2["kill_rank"] in RANK_LEGACY:
            cfg2["kill_rank"] = RANK_LEGACY[cfg2["kill_rank"]]
        # 旧版单槽兼容: heal_slot -> heal_slots 列表
        if cfg2.get("heal_slot", 0) and not cfg2.get("heal_slots"):
            cfg2["heal_slots"] = [int(cfg2["heal_slot"])]
        cfg2["heal_slots"] = [int(s) for s in cfg2.get("heal_slots", []) if int(s) in HEAL_NAMES]
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
    """问卷星风格单选: 选项列表鼠标点选(选中变蓝高亮), 底部[下一步]提交;
    返回选中的 key(未选/关窗口返回 None)"""
    result = {"v": None}
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    tk.Label(root, text=prompt, font=("Microsoft YaHei UI", 12), padx=24, pady=14,
             justify="left", wraplength=480).pack()
    sel = {}
    for key, label in options:
        v = tk.BooleanVar(value=False)
        b = tk.Label(root, text=label, font=("Microsoft YaHei UI", 11), padx=12, pady=6,
                     bg="#ffffff", relief="groove", borderwidth=1, anchor="w", cursor="hand2")
        b.pack(fill="x", padx=24, pady=3)
        b.bind("<Button-1>", lambda e, k=key, vv=v, bb=b: _pick(sel, k, vv, bb, multi=False))
        sel[key] = (v, b)
    tk.Button(root, text="下一步", font=("Microsoft YaHei UI", 11), width=22,
              command=lambda: (result.update(v=_submit(sel, multi=False)), root.destroy())[1]
              ).pack(pady=12, padx=24)
    root.eval("tk::PlaceWindow . center")
    try:
        root.mainloop()
    except Exception:
        pass
    return result["v"]


def _ask_multi(prompt, options, title, preselect=()):
    """问卷星风格多选: 选项列表鼠标点选切换(选中变蓝高亮+凹), 底部[下一步]提交;
    preselect: 默认勾选的 key 集合; 返回选中的 key 列表(关窗口返回 [])"""
    result = {"v": []}
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)
    tk.Label(root, text=prompt, font=("Microsoft YaHei UI", 12), padx=24, pady=14,
             justify="left", wraplength=480).pack()
    sel = {}
    for key, label in options:
        v = tk.BooleanVar(value=(key in preselect))
        b = tk.Label(root, text=label, font=("Microsoft YaHei UI", 11), padx=12, pady=6,
                     bg="#ffffff", relief="groove", borderwidth=1, anchor="w", cursor="hand2")
        b.pack(fill="x", padx=24, pady=3)
        b.bind("<Button-1>", lambda e, k=key, vv=v, bb=b: _pick(sel, k, vv, bb, multi=True))
        sel[key] = (v, b)
    tk.Button(root, text="下一步", font=("Microsoft YaHei UI", 11), width=22,
              command=lambda: (result.update(v=_submit(sel, multi=True)), root.destroy())[1]
              ).pack(pady=12, padx=24)
    root.eval("tk::PlaceWindow . center")
    try:
        root.mainloop()
    except Exception:
        pass
    return result["v"]


def _pick(sel, key, vv, bb, multi):
    """点选: 单选=先取消其他再选中(蓝底+凹), 多选=只切换自己"""
    if not multi:
        for k, (ov, ob) in sel.items():
            if ov.get():
                ov.set(False)
                ob.configure(bg="#ffffff", relief="groove")
    vv.set(not vv.get())
    bb.configure(bg="#d6e4ff" if vv.get() else "#ffffff",
                 relief="sunken" if vv.get() else "groove")


def _submit(sel, multi):
    """收集选中项: 单选返回第一个选中key(无则None), 多选返回列表"""
    if multi:
        return [k for k, (vv, _) in sel.items() if vv.get()]
    for k, (vv, _) in sel.items():
        if vv.get():
            return k
    return None


HEAL_COLOR_NAMES = {"rose/dahlia": "粉(玫瑰/大丽花)", "leaf/yucca": "绿(叶子/丝兰)", "starfish": "橙(海星)"}


def ask_heal_confirm(cand):
    """扫描到回血花瓣候选后: 弹窗勾选确认(默认全勾, 可取消误检的), 返回选中槽位列表(关窗口返回 None)
    cand: [(行号, 槽位1-10, 颜色名), ...]"""
    if not cand:
        return None
    options = [(f"{s}", f"槽位{s}（{'副' if r else '主'}行, {HEAL_COLOR_NAMES.get(c, c)}）") for r, s, c in cand]
    picked = _ask_multi("扫描到这些槽位可能有回血花瓣（颜色只是候选，U级花瓣也粉/普通级也绿）：\n取消勾选不是回血花瓣的槽位",
                        options, "回血花瓣确认", preselect=[str(s) for _, s, _ in cand])
    return [int(k) for k in picked]


def ask_update(cfg):
    """有存档时调用: 只问要不要更新(否→False 用旧设置)"""
    mode = MODE_NAMES.get(cfg.get("mode", "defense"), "?")
    rank = RANK_NAMES.get(cfg.get("kill_rank", "M"), "?")
    heal = ", ".join(HEAL_NAMES.get(s, "?") for s in cfg.get("heal_slots", [])) or "不用(没带回血)"
    htype = HEAL_TYPE_NAMES.get(cfg.get("heal_type", "rose"), "?")
    reg = cfg.get("region", "")
    reg_s = {"auto": "自动(按秒杀等级)"}.get(reg, reg) or "未设"
    ans = _ask("检测到已有设置：\n  模式：%s\n  打怪：%s\n  回血槽：%s\n  回血花瓣：%s\n  刷怪区域：%s\n\n要不要更新？" % (mode, rank, heal, htype, reg_s),
               [("yes", "更新设置"), ("no", "用旧设置继续")], "florr 挂机设置")
    return ans == "yes"


def ask_config(map_name="desert"):
    """首次/更新时调用: 依次问配置问题；map_name 用于列出刷怪区域"""
    m = _ask("你想全程攻击还是防御还是不弄？",
             [("attack", "全程攻击（按空格发射花瓣）"),
              ("defense", "全程防御（按住右键，花瓣绕身转）"),
              ("none", "不弄（纯手动操作）")], "florr 挂机设置 ①/⑥")
    if m is None:
        m = "defense"
    r = _ask("你可以秒（<3秒）哪个等级的怪？\\n（=这级自动追贴脸打，更高避开，更低不管）",
             [(k, RANK_NAMES[k]) for k in RANK_ORDER], "florr 挂机设置 ②/⑥")
    if r is None:
        r = "mythic"
    hs = _ask_multi("血量低时，切哪些副槽的回血花瓣（玫瑰/叶子）？\n（勾选所有放了回血花瓣的副槽位置，可多选；恢复后自动切回）",
                    [(i, HEAL_NAMES[i]) for i in range(1, 11)],
                    "florr 挂机设置 ③/⑥")
    ht = _ask("你带的是哪种回血花瓣？（决定低血触发时机）\n玫瑰Rose=爆发救急(20%触发)\n大丽花Dahlia=稳定小回血(30%触发)\n丝兰Yucca=仅防御时回血(20%触发, 跑路保持防御)\n海星Starfish=血<75%被动回(提前40%触发)\n叶子Leaf=已淘汰, 建议换玫瑰/丝兰",
              [("rose", "玫瑰 Rose（爆发救急，最常见）"),
               ("dahlia", "大丽花 Dahlia（稳定小回血）"),
               ("yucca", "丝兰 Yucca（防御时回血）"),
               ("starfish", "海星 Starfish（被动回血）"),
               ("leaf", "叶子 Leaf（过渡用）")], "florr 挂机设置 ④/⑥")
    if ht is None:
        ht = "rose"
    ef = _ask("刷怪效率模式？\n标准：更像人（更安全，效率约-8%）\n效率：少停顿少延迟（刷怪更快，挂机检测风险略升）",
              [("no", "标准（更安全）"), ("yes", "效率（刷怪更快）")], "florr 挂机设置 ⑤/⑥")
    lc = False
    if m != "none":
        lc = _ask("要不要蹭高等级怪的掉落？\n（打不动的M/U怪在附近时，上去打2.5秒混伤害拿掉落，然后撤退）\n掉落机制：总伤害>1%就有资格分掉落（单人时杀怪必得）",
                  [("no", "不蹭（更安全）"), ("yes", "蹭（掉落更多）")], "florr 挂机设置 ⑥/⑦") == "yes"
    rg = _ask("刷怪区域？（决定巡逻点，替代手动点选）\n自动=按你的秒杀等级推荐对应稀有度的区域\n手动=直接选这张图的区域\n（游戏里按 Alt 可看各区域稀有度，辅助选择）",
              region_options(map_name), "florr 挂机设置 ⑦/⑦")
    if rg is None:
        rg = "auto"
    return {"mode": m, "kill_rank": r, "heal_slots": hs, "efficiency": ef == "yes", "leech": lc, "heal_type": ht, "region": rg, "region_map": map_name, "version": 9}
