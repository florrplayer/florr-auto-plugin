# -*- coding: utf-8 -*-
"""
内存战斗模式 (v1.18.0)
直接读wasm内存的玩家+怪物世界坐标, 用WASD移动打怪
不用截图! 窗口最小化也能跑!
用法: py -3.12 main.py desert --memory
v1.18.0: 决策走 mob_db(稀有度反推/真实碰撞箱/追击范围/掉落价值) + 逃跑不往墙角跑
"""
import time, math, threading
import mob_db
from bridge_combat import (get_player, get_nearby_mobs, find_best_target,
                           wave_end_count)

# 危险怪type集合(统一走mob_db.DANGER_SIDS官方集)
_DANGER_TYPES = {mob_db.SID_TO_TYPE_ID[s] for s in mob_db.DANGER_SIDS
                 if s in mob_db.SID_TO_TYPE_ID}

# 键盘虚拟码 (WASD)
VK_W = 0x57; VK_A = 0x41; VK_S = 0x53; VK_D = 0x44
VK_RBUTTON = 0x02  # 鼠标右键(防御)

# 战斗参数
MAX_TARGET_DIST = 15000  # 全图找最近可杀目标 (奔袭打怪)
MIN_ATTACK_DIST = 150    # 距离150px时开始打
DANGER_DIST = 400        # 危险怪400px内就跑
STOP_DIST = 50           # 到50px内停下
CAN_KILL_HP = 800        # 能杀的HP上限
MAP_CENTER = (32500, 32500)  # 地图中心(逃跑偏向, 避免往墙角跑)
CENTER_BIAS = 0.35       # 逃跑方向偏向地图中心的强度


class MemoryBattle:
    def __init__(self, window):
        self.w = window
        self.player = None
        self.running = True

    def _keys_release(self):
        for vk in (VK_W, VK_A, VK_S, VK_D):
            self.w.key_up(vk)

    def _move_towards(self, dx, dy):
        """按方向按WASD"""
        self._keys_release()
        if abs(dx) > abs(dy):
            if dx > 0: self.w.key_down(VK_D)
            else:      self.w.key_down(VK_A)
        else:
            if dy > 0: self.w.key_down(VK_S)
            else:      self.w.key_down(VK_W)

    def _run_away(self, dx, dy, px, py):
        """反方向逃跑 + 偏向地图中心(不往墙角跑)"""
        self._keys_release()
        dlen = math.hypot(dx, dy)
        if dlen < 1:
            dx, dy = 0.3, 0.3
            dlen = math.hypot(dx, dy)
        # 远离危险怪的单位向量
        ax, ay = dx / dlen, dy / dlen
        # 偏向地图中心的单位向量
        cx, cy = MAP_CENTER[0] - px, MAP_CENTER[1] - py
        clen = math.hypot(cx, cy)
        if clen > 1:
            cx, cy = cx / clen, cy / clen
            ax = ax + CENTER_BIAS * cx
            ay = ay + CENTER_BIAS * cy
        if abs(ax) > abs(ay):
            if ax < 0: self.w.key_down(VK_A)   # v1.18.3: 修方向反转(ax<0=逃向-x=按A向左, 原来按D送死)
            else:      self.w.key_down(VK_D)
        else:
            if ay < 0: self.w.key_down(VK_W)   # v1.18.3: 修方向反转(ay<0=逃向-y=按W向上)
            else:      self.w.key_down(VK_S)

    def _move_dir(self, d):
        """按指定方向移动 (w/a/s/d)"""
        self._keys_release()
        self.w.key_down({'w': VK_W, 'a': VK_A, 's': VK_S, 'd': VK_D}[d])

    def battle_loop(self):
        """战斗主循环: 每200ms读一次wasm内存"""
        print("[内存战斗] 启动, 每200ms读一次游戏内存 (玩家=camera地址, 怪=type id)")
        # 持续右键防御 (回血花瓣海星/丝兰在防御时回血)
        try: self.w.key_down(VK_RBUTTON)
        except: pass
        last_move = time.time()
        # v1.21.2: Super出生公告雷达 (bridge聊天 -> 全图扫Super)
        try:
            from super_ping import SuperPing
            self.super_ping = SuperPing()
        except Exception:
            self.super_ping = None
        while self.running:
            try:
                # 读玩家 (camera = 精确世界坐标)
                self.player = get_player()
                if not self.player:
                    time.sleep(0.2); continue
                px, py = self.player['x'], self.player['y']

                # 读怪物
                mobs, _ = get_nearby_mobs()

                # 危险检测: 危险怪进入它的追击范围就跑 (每只怪用自己的aggro)
                danger = [m for m in mobs if m['type'] in _DANGER_TYPES
                          and math.hypot(m['x']-px, m['y']-py) < max(DANGER_DIST, m.get('aggro', 255) * 1.5)]
                if danger:
                    d = danger[0]
                    dx, dy = px - d['x'], py - d['y']
                    print(f"[躲] 危险怪({d['cn']} {d.get('rarity','')}) {math.hypot(d['x']-px,d['y']-py):.0f}px, 逃跑(偏中心)")
                    self._run_away(dx, dy, px, py)
                    time.sleep(0.2)
                    continue

                # 选目标: mob_db综合评分 (秒杀优先+特殊怪5倍+掉落价值+距离)
                target = find_best_target(px, py, can_kill_hp=CAN_KILL_HP, max_dist=MAX_TARGET_DIST)

                # v1.21.2: Super公告雷达 - 每帧喂bridge聊天, 命中公告开启全图扫Super
                if self.super_ping is not None:
                    try:
                        bd = bridge_combat._fetch_latest()
                        chat = bd.get('chat') or []
                        for msg in chat[-3:]:
                            hit = self.super_ping.feed(msg)
                            if hit:
                                sid, cn, pos = hit
                                print(f"[Super雷达] 公告: {cn} Super 已出生! {'公告位置:'+str(pos) if pos else '全图扫120s'} (去抢!)")
                    except Exception:
                        pass
                    if self.super_ping.is_hunting():
                        # 猎杀期: 扩大目标距离+提高Super目标权重
                        hunt = self.super_ping.super_hunt_sid
                        if hunt and target and target.get('sid') != hunt:
                            t2 = find_best_target(px, py, can_kill_hp=CAN_KILL_HP,
                                                  max_dist=MAX_TARGET_DIST * 3, force_sid=hunt)
                            if t2:
                                target = t2
                        elif not target:
                            t2 = find_best_target(px, py, can_kill_hp=CAN_KILL_HP,
                                                  max_dist=MAX_TARGET_DIST * 3, force_sid=hunt)
                            if t2:
                                target = t2

                # AI规则-波末: 同屏<=4只时全体怪冲玩家, 停手原地防御接怪
                if target is None:
                    n_wave = wave_end_count(max_dist=2500)
                    if 0 < n_wave <= 4:
                        if time.time() - last_move > 4:
                            print(f"[波末] 同屏只剩{n_wave}只, 原地防御等刷新(不冲)")
                            last_move = time.time()
                        time.sleep(0.4)
                        continue

                if target:
                    dist = math.hypot(target['x']-px, target['y']-py)
                    spd = mob_db.get_aggro_speed(target['sid'])   # AI研究: 追击速度系数(≥1.0=追得上玩家)
                    # 追得上的怪(冲撞/毒)不能站桩贴脸(接触伤害白嫖), 用打带跑: 蹭1下立刻拉开
                    hit_run = (spd >= 1.0) and (target.get('score', 0) < 1000)
                    if hit_run and dist > STOP_DIST:
                        dx, dy = target['x']-px, target['y']-py
                        self._move_towards(dx, dy)
                        print(f"[打带跑] {target['cn']}({target.get('rarity','')}) 追击速度{spd:.2f} 距离{dist:.0f}")
                        last_move = time.time()
                    elif hit_run and dist <= STOP_DIST:
                        # 贴到跟前打一下立刻撤 (0.8s输出后反向拉开)
                        self._keys_release()
                        now = time.time()
                        if now - last_move > 0.8:
                            self._run_away(px-target['x'], py-target['y'], px, py)
                            print(f"[打带跑] 蹭完即撤")
                            last_move = now
                        else:
                            # 输出窗口内保持静止(防御状态的花瓣在打)
                            time.sleep(0.15)
                    elif dist > STOP_DIST:
                        dx, dy = target['x']-px, target['y']-py
                        self._move_towards(dx, dy)
                        print(f"[打] {target['cn']}({target.get('rarity','')}) hp={target['hp']} 距离{dist:.0f} 评分{target.get('score',0):.0f}")
                        last_move = time.time()
                    else:
                        # 到跟前了, 停下输出
                        self._keys_release()
                        if time.time() - last_move > 1:
                            print(f"[打] {target['cn']} 已贴身")
                            last_move = time.time()
                else:
                    # 没目标: 朝沙漠中部怪区(北)持续走, 每5秒重新找
                    if time.time() - last_move > 5:
                        print("[找] 附近没可杀怪, 朝怪区(北)行进")
                        self._move_dir('w')
                        last_move = time.time()
                    time.sleep(0.5)

            except Exception as e:
                print(f"[err] {e}")
            time.sleep(0.15)

    def stop(self):
        self.running = False
        self._keys_release()
        try: self.w.key_up(VK_RBUTTON)
        except: pass


def run_memory_battle(window, duration=None):
    """在main.py里调用: 运行内存战斗"""
    battle = MemoryBattle(window)
    t = threading.Thread(target=battle.battle_loop, daemon=True)
    t.start()
    print("[+] 内存战斗模式运行中... Ctrl+C停止")
    try:
        while battle.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        battle.stop()
    return battle


if __name__ == '__main__':
    # 独立测试
    import window_ctrl
    w = window_ctrl.get_window()
    print(f"窗口: {w.title if hasattr(w,'title') else 'ok'}")
    run_memory_battle(w)
