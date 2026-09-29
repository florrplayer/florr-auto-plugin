# -*- coding: utf-8 -*-
"""分析WebSocket游戏状态快照的二进制协议"""
import json, os

with open(r"C:\Users\intel\Downloads\florr-auto-pathing-main\data\ws_state_snapshots.json","r") as f:
    snapshots = json.load(f)

print(f"快照数: {len(snapshots)}")
print(f"每条长度: {[len(s) for s in snapshots]}")

# 分析channel字节
print("\n=== Channel字节统计 ===")
channels = {}
for s in snapshots:
    ch = s[0]
    channels[ch] = channels.get(ch, 0) + 1
print(f"Channel分布: {channels}")

# 看每条消息的长度变化
lens = [len(s) for s in snapshots]
print(f"\n长度范围: {min(lens)}-{max(lens)}, 均值: {sum(lens)//len(lens)}")

# 按channel分组分析
for ch in channels:
    group = [s for s in snapshots if s[0] == ch]
    print(f"\n=== Channel {ch} ({len(group)}条) ===")
    # 看前20字节的统计
    if group:
        print(f"  前20字节样本(第一条): {group[0][:20]}")
        print(f"  前20字节样本(第二条): {group[1][:20] if len(group)>1 else 'N/A'}")
        # 字节熵
        import collections
        all_bytes = []
        for s in group:
            all_bytes.extend(s[1:20])  # 跳过channel字节
        c = collections.Counter(all_bytes)
        unique = len(c)
        print(f"  前19字节(除channel)唯一值数: {unique}/256")

# 尝试找玩家坐标 - 搜索已知值附近的浮点数
# 玩家在沙漠，坐标未知，但HP应该是一个整数
print("\n=== 搜索可能的HP值 ===")
for i, s in enumerate(snapshots[:5]):
    # 找16位整数模式
    for j in range(0, len(s)-2, 2):
        val = s[j] | (s[j+1] << 8)
        if 100 < val < 5000:  # HP范围
            print(f"  快照{i} 偏移{j}: 16位值={val}")
