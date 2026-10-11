# -*- coding: utf-8 -*-
from PIL import Image
import os
ico = Image.open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\assets\autoflorr.ico')
sizes = ico.info.get('sizes')
size = os.path.getsize(r'C:\Users\intel\Downloads\florr-auto-pathing-main\assets\autoflorr.ico')
with open(r'C:\Users\intel\Downloads\florr-auto-pathing-main\assets\_ico_check.txt', 'w', encoding='utf-8') as f:
    f.write(f'ico 内含尺寸: {sizes}\n文件大小: {size} bytes\n')
