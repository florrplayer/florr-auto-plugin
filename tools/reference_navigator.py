"""
Navigator - 自动导航器
使用Lazy Theta*算法进行智能路径规划
"""

import os
import time
import math
import heapq
from typing import Optional, Dict, Any, List, Tuple, Set
import numpy as np

from ..base import BaseModule, ModuleState


class Navigator(BaseModule):
    name = 'navigator'
    version = '1.0.0'
    description = '自动导航器'
    priority = 85
    dependencies = ['map_classifier']
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        self._target_map = self.get_config('target_map', 'ocean')
        self._auto_navigate = self.get_config('auto_navigate', False)
        self._avoid_danger = self.get_config('avoid_danger', True)
        self._check_interval = self.get_config('check_interval', 0.3)
        
        self._current_path: List[Tuple[int, int]] = []
        self._current_target: Optional[Tuple[int, int]] = None
        self._player_pos: Optional[Tuple[float, float]] = None
        self._grid_size = 20
        self._navigation_count = 0
        self._stuck_count = 0
        self._last_pos: Optional[Tuple[float, float]] = None
        self._last_move_time = 0
    
    def _on_start(self):
        self._subscribe_events()
        self._log('导航器已启动')
    
    def _on_stop(self):
        self._current_path = []
        self._log('导航器已停止')
    
    def _on_tick(self):
        try:
            self._update_player_position()
            
            if self._auto_navigate and self._current_target:
                self._navigate_to_target()
            
            self._check_stuck()
            
            time.sleep(self._check_interval)
            
        except Exception as e:
            self._log(f'导航错误: {e}', level='ERROR')
            time.sleep(1)
    
    def _subscribe_events(self):
        from ...core.events import EventBus
        event_bus = EventBus()
        event_bus.subscribe('map.changed', self._on_map_changed)
    
    def _on_map_changed(self, event):
        map_name = event.data.get('map')
        self._log(f'地图切换: {map_name}')
        
        if self._auto_navigate and map_name != self._target_map:
            self._log(f'目标地图: {self._target_map}，需要导航')
    
    def _update_player_position(self):
        from ...core.platform import PlatformManager
        platform = PlatformManager()
        
        screenshot = platform.capture_screen()
        if screenshot is not None:
            self._player_pos = self._detect_player_position(screenshot)
    
    def _detect_player_position(self, image: np.ndarray) -> Optional[Tuple[float, float]]:
        try:
            import cv2
            
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            lower_pink = np.array([150, 50, 50])
            upper_pink = np.array([180, 255, 255])
            
            mask = cv2.inRange(hsv, lower_pink, upper_pink)
            
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                
                if M['m00'] > 0:
                    cx = M['m10'] / M['m00']
                    cy = M['m01'] / M['m00']
                    return (cx, cy)
        except Exception as e:
            self._log(f'玩家位置检测错误: {e}', level='WARNING')
        
        return None
    
    def _navigate_to_target(self):
        if not self._player_pos or not self._current_target:
            return
        
        px, py = self._player_pos
        tx, ty = self._current_target
        
        distance = math.sqrt((tx - px) ** 2 + (ty - py) ** 2)
        
        if distance < 30:
            self._log('已到达目标位置')
            self._current_target = None
            self._current_path = []
            return
        
        if not self._current_path:
            self._current_path = self._find_path(
                (int(px), int(py)),
                (int(tx), int(ty))
            )
        
        if self._current_path:
            next_point = self._current_path[0]
            self._move_towards(next_point)
            
            if self._is_near_point(next_point, 20):
                self._current_path.pop(0)
    
    def _find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        return self._lazy_theta_star(start, goal)
    
    def _lazy_theta_star(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0}
        f_score: Dict[Tuple[int, int], float] = {start: self._heuristic(start, goal)}
        
        open_set_hash: Set[Tuple[int, int]] = {start}
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            open_set_hash.discard(current)
            
            if self._is_near_point(current, goal, self._grid_size):
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self._get_neighbors(current):
                tentative_g = g_score[current] + self._distance(current, neighbor)
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)
        
        return []
    
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    
    def _distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return self._heuristic(a, b)
    
    def _get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        x, y = pos
        neighbors = []
        
        for dx in [-self._grid_size, 0, self._grid_size]:
            for dy in [-self._grid_size, 0, self._grid_size]:
                if dx == 0 and dy == 0:
                    continue
                neighbors.append((x + dx, y + dy))
        
        return neighbors
    
    def _reconstruct_path(self, came_from: Dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _move_towards(self, target: Tuple[int, int]):
        from ...core.platform import PlatformManager
        platform = PlatformManager()
        
        if not self._player_pos:
            return
        
        px, py = self._player_pos
        tx, ty = target
        
        dx = tx - px
        dy = ty - py
        
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance == 0:
            return
        
        dx /= distance
        dy /= distance
        
        move_distance = min(distance, 50)
        
        platform.key_press('w') if dy < -0.3 else None
        platform.key_press('s') if dy > 0.3 else None
        platform.key_press('a') if dx < -0.3 else None
        platform.key_press('d') if dx > 0.3 else None
    
    def _is_near_point(self, point: Tuple[int, int], target: Tuple[int, int], threshold: float = 10) -> bool:
        return self._heuristic(point, target) < threshold
    
    def _check_stuck(self):
        if not self._player_pos:
            return
        
        current_time = time.time()
        
        if self._last_pos:
            distance = self._heuristic(
                (int(self._player_pos[0]), int(self._player_pos[1])),
                (int(self._last_pos[0]), int(self._last_pos[1]))
            )
            
            if distance < 5 and current_time - self._last_move_time > 3:
                self._stuck_count += 1
                self._log(f'检测到卡住 ({self._stuck_count}次)', level='WARNING')
                self._handle_stuck()
        
        self._last_pos = self._player_pos
        self._last_move_time = current_time
    
    def _handle_stuck(self):
        from ...core.platform import PlatformManager
        platform = PlatformManager()
        
        platform.key_press('space')
        time.sleep(0.2)
        
        import random
        direction = random.choice(['w', 's', 'a', 'd'])
        platform.key_press(direction)
        time.sleep(0.3)
        
        self._current_path = []
    
    def set_target(self, x: int, y: int):
        self._current_target = (x, y)
        self._current_path = []
        self._log(f'设置目标: ({x}, {y})')
    
    def stop_navigation(self):
        self._current_target = None
        self._current_path = []
        self._log('停止导航')
    
    def _log(self, message: str, level: str = 'INFO'):
        from ...core.logger import Logger
        logger = Logger()
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, module='Navigator')
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'current_target': self._current_target,
            'player_pos': self._player_pos,
            'path_length': len(self._current_path),
            'navigation_count': self._navigation_count,
            'stuck_count': self._stuck_count
        }
