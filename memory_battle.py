# -*- coding: utf-8 -*-
"""
内存战斗模式 (v1.18.0)
直接读wasm内存的玩家+怪物世界坐标, 用WASD移动打怪
不用截图! 窗口最小化也能跑!
用法: py -3.12 main.py desert --memory
v1.18.0: 决策走 mob_db(稀有度反推/真实碰撞箱/追击范围/掉落价值) + 逃跑不往墙角跑
v1.24.0: bot式侧移避怪 + v1.24.1 导弹射程撤出 + v1.24.5 修NameError
v1.25.2: 深度用AI研究§8 - 目标粘滞+传送门3秒无敌窗+蟑螂螃蟹打带跑
v1.27.0: Mythic走位表(florr-auto-farm实测) - Mythic甲虫/火兵蚁/蝎子/沙蜈蚣 strafe/ram 打带跑
"""
import time, math, threading
import mob_db
import combat_strategy  # v1.27.0: Mythic走位表(strafe/ram/hold)
from bridge_combat import (get_player, get_nearby_mobs, find_best_target,
                           wave_end_count)
import bridge_combat  # v1.24.5: 修 NameError (第201行 bridge_combat._fetch_latest 需要模块名)

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

    def _send_chat_text(self, text):
        """发聊天消息(全键盘): Enter开输入框 -> 剪贴板粘贴 -> Enter发送 (v1.23.3 Boss喊话用)"""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            import time as _t
            self.w.key_down(0x0D); _t.sleep(0.05); self.w.key_up(0x0D)
            _t.sleep(0.3)
            self.w.key_down(0x11); self.w.key_down(0x56)
            _t.sleep(0.05); self.w.key_up(0x56); self.w.key_up(0x11)
            _t.sleep(0.3)
            self.w.key_down(0x0D); _t.sleep(0.05); self.w.key_up(0x0D)
            return True
        except Exception as e:
            print(f"[聊天] 发送失败: {e}")
            return False

    # v1.24.0: bot式侧移避怪(bot_ai.cpp移植) - 追击时前方有怪不撞上去, 侧移绕过
    AVOID_MARGIN = 26.0       # kBotMobAvoidMargin
    AVOID_LOOKAHEAD = 110.0   # kBotMobAvoidLookahead
    AVOID_TANGENT = 0.85      # kBotMobAvoidTangent
    AVOID_DEADBAND = 30.0     # kBotMobAvoidSideDeadband
    AVOID_RADIUS = 260.0      # kBotMobAvoidQueryRadius
    PLAYER_R = 20.0           # kPlayerBaseRadius

    def _bot_avoid(self, px, py, tx, ty, mobs):
        """正前方有怪挡路 -> 侧移绕过(不减速不撞); 返回True表示本次改走侧移"""
        heading_x, heading_y = tx - px, ty - py
        hlen = math.hypot(heading_x, heading_y)
        if hlen < 1:
            return False
        fx, fy = heading_x / hlen, heading_y / hlen
        lx, ly = -fy, fx   # 左向量
        best = None
        for m in mobs or []:
            mx, my = m.get('x', 0), m.get('y', 0)
            tox, toy = mx - px, my - py
            dist = math.hypot(tox, toy)
            if dist < 1:
                continue
            ahead = (tox * fx + toy * fy) / dist   # 归一化前方分量
            if ahead <= 0.0:
                continue   # 在身后不挡路
            mr = m.get('radius') or m.get('r') or 10.0
            ring = self.PLAYER_R + mr + self.AVOID_MARGIN
            outer = ring + self.AVOID_LOOKAHEAD
            if dist >= outer:
                continue
            strength = min(2.0, (outer - dist) / self.AVOID_LOOKAHEAD)
            lateral = (tox * lx + toy * ly) / dist
            side = -1.0 if abs(lateral) < self.AVOID_DEADBAND / 100.0 else (-1.0 if lateral >= 0 else 1.0)
            headOn = min(1.0, ahead)
            blend = headOn * self.AVOID_TANGENT
            push_x, push_y = -tox / dist, -toy / dist   # 推离
            sx, sy = lx * side, ly * side                # 侧移
            # 混合: 推离*(1-blend) + 侧移*strength*blend
            ox = push_x * (1.0 - blend) + sx * strength * blend
            oy = push_y * (1.0 - blend) + sy * strength * blend
            # 偏置(不反转意图): 目标方向 + 0.6*偏置
            dx = fx + ox * 0.6
            dy = fy + oy * 0.6
            if best is None or dist < best[0]:
                best = (dist, dx, dy, m)
        if best is None:
            return False
        _, dx, dy, m = best
        self._keys_release()
        if abs(dx) > abs(dy):
            if dx > 0: self.w.key_down(VK_D)
            else:      self.w.key_down(VK_A)
        else:
            if dy > 0: self.w.key_down(VK_S)
            else:      self.w.key_down(VK_W)
        print(f"[侧移] 绕开 {m.get('cn','怪')}({m.get('rarity','')}) 距离{best[0]:.0f}")
        return True

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
        # v1.25.2: 目标粘滞(AI研究§8.1-2 仇恨随存活增长->单目标速杀防拉扯) + 传送门3秒无敌窗(§8.1-6)
        self._sticky_sid = None
        self._last_px = self._last_py = None
        self._invuln_until = 0.0
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

                # v1.25.2 传送门3秒无敌窗口: 坐标突变=跨图, 传送门出来3秒敌对怪中立化(§8.1-6)
                if self._last_px is not None:
                    jump = math.hypot(px - self._last_px, py - self._last_py)
                    if jump > 2000:
                        self._invuln_until = time.time() + 3.0
                        print(f"[传送] 检测到跨图位移{jump:.0f}px, 3秒无敌窗口原地防御重校准")
                self._last_px, self._last_py = px, py
                if time.time() < self._invuln_until:
                    self._keys_release()
                    time.sleep(0.25)
                    continue

                # 读怪物
                mobs, _ = get_nearby_mobs()

                # 危险检测: 危险怪进入它的追击范围就跑 (每只怪用自己的aggro)
                danger = [m for m in mobs if m['type'] in _DANGER_TYPES
                          and math.hypot(m['x']-px, m['y']-py) < max(DANGER_DIST, m.get('aggro', 255) * 1.5)]
                if danger:
                    d = danger[0]
                    dx, dy = px - d['x'], py - d['y']
                    # v1.25.2: 逃跑时清掉粘滞目标(保命优先, 回来再选)
                    self._sticky_sid = None
                    print(f"[躲] 危险怪({d['cn']} {d.get('rarity','')}) {math.hypot(d['x']-px,d['y']-py):.0f}px, 逃跑(偏中心)")
                    self._run_away(dx, dy, px, py)
                    time.sleep(0.2)
                    continue

                # 选目标: mob_db综合评分 (秒杀优先+特殊怪5倍+掉落价值+距离+粘滞)
                target = find_best_target(px, py, can_kill_hp=CAN_KILL_HP, max_dist=MAX_TARGET_DIST,
                                          sticky_sid=self._sticky_sid)
                # v1.25.2: 更新粘滞(目标换了才更新, 打死了自然消失)
                if target is not None:
                    if target['sid'] != self._sticky_sid:
                        print(f"[粘滞] 目标锁定 {target['cn']}({target['rarity']}) 不再频繁换怪")
                    self._sticky_sid = target['sid']

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
                                # v1.23.3: 真人喊话(Boss闲聊模板, 防挂机+像玩家)
                                try:
                                    from chat_solver import BOSS_SHOUTS_SUPER, BOSS_SHOUTS_UNIQUE
                                    import random as _r
                                    pool = BOSS_SHOUTS_SUPER
                                    text = _r.choice(pool).replace('{tier}', 'super').replace('{mob}', sid.replace('_', ' '))
                                    self._send_chat_text(text)
                                except Exception:
                                    pass
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
                    # v1.23.7: stinger/导弹怪(黄蜂/胡蜂/螳螂)也进打带跑 - 摆尾蓄力250ms闪避窗
                    # v1.25.2: +蟑螂(受击爆发冲撞)/螃蟹(40%血冲刺)(AI研究§8.2-12/13) -> 打带跑横移
                    # v1.27.0: +Mythic走位表(florr-auto-farm实测) - Mythic甲虫/火兵蚁/蝎子/沙蜈蚣 strafe/ram 打带跑, 不站桩被秒
                    ai_info = mob_db.mob_ai_info(target['sid'])
                    mythic_kite = combat_strategy.mythic_kite(target['sid'])
                    dash_dodge = target['sid'] in ('roach', 'crab', 'crab_mecha') or (
                        mythic_kite in ('strafe', 'ram') and target.get('rarity') == 'Mythic')
                    stinger_dodge = bool(ai_info.get('stinger') or ai_info.get('projectile')) or dash_dodge
                    # 追得上的怪(冲撞/毒)或远程导弹怪不能站桩贴脸(接触伤害/导弹白嫖), 用打带跑: 蹭1下立刻拉开
                    hit_run = (spd >= 1.0 or stinger_dodge) and (target.get('score', 0) < 1000)
                    if hit_run:
                        # v1.24.1: 导弹怪在射程内优先持续撤出(黄蜂333/螳螂500), 撤到射程外才回冲输出
                        mrange = mob_db.missile_range(target['sid']) if stinger_dodge else None
                        if stinger_dodge and mrange and dist <= mrange + 10:
                            if time.time() - last_move > 0.35:
                                self._run_away(px-target['x'], py-target['y'], px, py)
                                print(f"[打带跑] 撤出导弹射程({mrange:.0f}) 当前{dist:.0f}")
                                last_move = time.time()
                            else:
                                time.sleep(0.15)
                        elif dist > STOP_DIST:
                            dx, dy = target['x']-px, target['y']-py
                            self._move_towards(dx, dy)
                            print(f"[打带跑] {target['cn']}({target.get('rarity','')}) 追击速度{spd:.2f} 距离{dist:.0f}" + (' [横闪]' if stinger_dodge else ''))
                            last_move = time.time()
                        else:
                            # 贴到跟前打一下立刻撤 (stinger: 0.3s输出窗对齐250ms蓄力, 其他0.8s)
                            self._keys_release()
                            now = time.time()
                            hold = 0.3 if stinger_dodge else 0.8
                            if now - last_move > hold:
                                self._run_away(px-target['x'], py-target['y'], px, py)
                                print(f"[打带跑] 蹭完即撤" + (' (闪避窗0.3s)' if stinger_dodge else ''))
                                last_move = now
                            else:
                                # 输出窗口内保持静止(防御状态的花瓣在打)
                                time.sleep(0.15)
                    elif dist > STOP_DIST:
                        dx, dy = target['x']-px, target['y']-py
                        # v1.24.0: bot式侧移避怪 - 前方有怪挡路先绕, 不撞上去
                        if not self._bot_avoid(px, py, target['x'], target['y'],
                                               get_nearby_mobs(self.player, max_dist=300)):
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
