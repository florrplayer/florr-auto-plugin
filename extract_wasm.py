import re

with open('wasm_dump/all_strings.txt', 'r', encoding='utf-8') as f:
    strings = f.read().splitlines()

# 找中文翻译
cn_strings = []
for s in strings:
    if re.search(r'[\u4e00-\u9fff]', s) and len(s) > 3:
        cn_strings.append(s)

print(f"=== 中文字符串 ({len(cn_strings)}) ===")
for s in sorted(set(cn_strings))[:80]:
    print(f"  {s[:120]}")

# 找数字配置
print(f"\n=== 数值配置 ===")
for s in strings:
    if re.search(r'\d+\.?\d*', s) and len(s) < 80 and any(k in s.lower() for k in ['hp','health','damage','speed','radius','armor','heal','cooldown','xp','drop','cost']):
        print(f"  {s}")
