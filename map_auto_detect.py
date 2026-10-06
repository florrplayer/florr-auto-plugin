# -*- coding: utf-8 -*-
"""
地图自动识别 v1.25.0 (移植自 florr_assistant/modules/pathing/map_classifier.py, 纯函数轻量版)
原理: 右上角(35%x40%)小地图区域 + 多尺度金字塔模板匹配(0.5~2.0x) + 置信度排序
用法: from map_auto_detect import detect_map, get_map_label
  result = detect_map(frame)  # -> {'map':'desert','confidence':0.83,'scale':1.2,'all_scores':{...}} 或 None
启动时自动识别当前地图, 与玩家参数/存档不一致时提示(防止进错图跑错巡逻点/掉落表)
模板: resources/maps/*.png (9张: garden/desert/ocean/jungle/anthell/hel/sewers/factory/worm's inside)
"""
import os
import base64
import cv2
import numpy as np

try:
    from map_templates_b64 import TEMPLATES_B64 as _B64
except Exception:
    _B64 = {}

_MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'maps')
_DEFAULT_SCALES = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]
_COARSE_SCALES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

# 模板文件名 -> 插件地图名(可映射到 apply_map / 掉落表 key)
_MAP_ALIAS = {
    'garden': 'garden', 'desert': 'desert', 'ocean': 'ocean', 'jungle': 'jungle',
    'anthell': 'anthell', 'hel': 'hel', 'sewers': 'sewers',
    'factory': 'factory', "worm's inside": 'worm',
}
# 中文显示名
_MAP_CN = {
    'garden': '后花园', 'desert': '沙漠', 'ocean': '水域', 'jungle': '丛林',
    'anthell': '蚂蚁地狱', 'hel': '冥界', 'sewers': '下水道',
    'factory': '工厂', 'worm': '蠕虫体内',
}

_templates = None


def _load_templates():
    """懒加载模板: 优先 resources/maps/*.png, 缺失时用内置 base64(GitHub 分发免二进制)"""
    global _templates
    if _templates is not None:
        return _templates
    _templates = {}
    if os.path.isdir(_MAPS_DIR):
        for fn in os.listdir(_MAPS_DIR):
            if not fn.lower().endswith('.png'):
                continue
            key = fn[:-4]
            tpl = cv2.imread(os.path.join(_MAPS_DIR, fn), cv2.IMREAD_COLOR)
            if tpl is not None:
                _templates[key] = tpl
    if not _templates and _B64:
        for key, b64 in _B64.items():
            buf = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
            tpl = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if tpl is not None:
                _templates[key] = tpl
    return _templates


def _multi_scale_match(image, template, scales=None):
    """多尺度 matchTemplate: 返回 (best_val, best_loc, best_scale, matched_size)"""
    if scales is None:
        scales = _DEFAULT_SCALES
    th, tw = template.shape[:2]
    ih, iw = image.shape[:2]
    best_val, best_loc, best_scale, best_size = 0.0, (0, 0), 1.0, (0, 0)
    for scale in scales:
        nw, nh = int(tw * scale), int(th * scale)
        if nw < 10 or nh < 10 or nh > ih or nw > iw:
            continue
        rs = cv2.resize(template, (nw, nh),
                        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        res = cv2.matchTemplate(image, rs, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_val:
            best_val, best_loc, best_scale, best_size = max_val, max_loc, scale, (nw, nh)
    return best_val, best_loc, best_scale, best_size


def _pyramid_search(image, template, threshold=0.5):
    """粗匹配(0.5~2.0)后细扫(±0.2步进0.05)"""
    coarse = _multi_scale_match(image, template, _COARSE_SCALES)
    cv, cl, cs, csz = coarse
    if cv < threshold:
        return coarse
    fine_scales = []
    step = 0.05
    s = max(0.3, cs - 0.2)
    while s <= cs + 0.2 + step:
        fine_scales.append(round(s, 2))
        s += step
    fine = _multi_scale_match(image, template, fine_scales)
    if fine[0] > cv:
        return fine
    return coarse


def _search_region(screenshot):
    """右上角区域(florr 小地图实测位置: 右边缘附近 y~144 高~282)
    用 45%宽 x 65%高 覆盖 300x300 小地图 + 缩放余量"""
    h, w = screenshot.shape[:2]
    sw, sh = int(w * 0.45), int(h * 0.65)
    return (w - sw, 0, w, sh)


def match(screenshot, threshold=0.5, use_pyramid=True):
    """全模板匹配, 返回最佳 MatchResult dict 或 None"""
    tpls = _load_templates()
    if screenshot is None or not tpls:
        return None
    x1, y1, x2, y2 = _search_region(screenshot)
    search = screenshot[y1:y2, x1:x2]
    best = None
    for key, template in tpls.items():
        if use_pyramid:
            mv, ml, ms, msz = _pyramid_search(search, template, threshold)
        else:
            mv, ml, ms, msz = _multi_scale_match(search, template)
        if best is None or mv > best['confidence']:
            if mv >= threshold:
                best = {
                    'template': key, 'map': _MAP_ALIAS.get(key, key),
                    'confidence': float(mv), 'scale': ms,
                    'top_left': (ml[0] + x1, ml[1] + y1),
                    'size': msz,
                }
    return best


def match_all(screenshot, threshold=0.3, use_pyramid=True):
    """返回所有>=threshold的匹配, 按置信度降序"""
    tpls = _load_templates()
    if screenshot is None or not tpls:
        return []
    x1, y1, x2, y2 = _search_region(screenshot)
    search = screenshot[y1:y2, x1:x2]
    out = []
    for key, template in tpls.items():
        if use_pyramid:
            mv, ml, ms, msz = _pyramid_search(search, template, threshold)
        else:
            mv, ml, ms, msz = _multi_scale_match(search, template)
        if mv >= threshold:
            out.append({'template': key, 'map': _MAP_ALIAS.get(key, key),
                        'confidence': float(mv), 'scale': ms,
                        'top_left': (ml[0] + x1, ml[1] + y1), 'size': msz})
    out.sort(key=lambda r: r['confidence'], reverse=True)
    return out


def detect_map(screenshot, threshold=0.5):
    """一行调用: 返回 {'map','confidence','scale','all_scores'} 或 None"""
    best = match(screenshot, threshold=threshold)
    if best is None:
        return None
    all_scores = {r['map']: round(r['confidence'], 3) for r in match_all(screenshot, threshold=0.3)}
    return {'map': best['map'], 'confidence': best['confidence'],
            'scale': best['scale'], 'all_scores': all_scores}


def get_map_label(key):
    return _MAP_CN.get(key, key)


def draw_match(screenshot, result, color=(0, 255, 0)):
    """画匹配框(调试用)"""
    out = screenshot.copy()
    x1, y1 = result['top_left']
    w, h = result['size']
    cv2.rectangle(out, (x1, y1), (x1 + w, y1 + h), color, 2)
    label = f"{result['map']}: {result['confidence']:.2f} ({result['scale']:.2f}x)"
    cv2.putText(out, label, (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return out


if __name__ == '__main__':
    print(f"模板目录: {_MAPS_DIR} 存在={os.path.isdir(_MAPS_DIR)}")
    print(f"加载模板: {sorted(_load_templates().keys())}")
    # 自测: 全图匹配(模板自身)应 100% 命中; 再测右上角搜索(模拟真实截图)
    def _full_match(image, threshold=0.5):
        """全图匹配(无搜索区域限制)"""
        tpls = _load_templates()
        best = None
        for key, template in tpls.items():
            mv, ml, ms, msz = _pyramid_search(image, template, threshold)
            if mv >= threshold and (best is None or mv > best['confidence']):
                best = {'map': _MAP_ALIAS.get(key, key), 'confidence': float(mv)}
        return best
    print("--- 全图匹配自测(应全中) ---")
    for key, tpl in _load_templates().items():
        r = _full_match(tpl)
        ok = r and r['map'] == _MAP_ALIAS.get(key, key)
        print(f"  {key:16s} -> {r['map'] if r else 'None':10s} conf={r['confidence'] if r else 0:.2f} {'✓' if ok else '✗'}")
    # 模拟真实截图: 1365x672 黑色画布, 把 desert 模板放在右上角小地图位置
    print("--- 模拟真实截图(desert 模板放右上角) ---")
    canvas = np.zeros((672, 1365, 3), dtype=np.uint8)
    tpl = _load_templates()['desert']
    canvas[40:340, 1000:1300] = tpl
    r = detect_map(canvas)
    print(f"  detect_map -> {r['map'] if r else 'None'} conf={r['confidence'] if r else 0:.2f} "
          f"{'✓' if r and r['map'] == 'desert' else '✗'}")
    if r:
        print(f"  all_scores={r['all_scores']}")
