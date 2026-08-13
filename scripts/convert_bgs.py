#!/usr/bin/env python3
"""Painted PNGs -> optimized jpgs in assets/."""
from PIL import Image
import os

ASSETS = '/home/hermes/goominhos/assets'
for i in range(1, 7):
    im = Image.open(f'/tmp/goo_gen/bg{i}.png').convert('RGB')
    im = im.resize((1600, 900), Image.LANCZOS)
    im.save(f'{ASSETS}/bg{i}.jpg', quality=85)
    print(f'bg{i}.jpg', os.path.getsize(f'{ASSETS}/bg{i}.jpg') // 1024, 'KB')
