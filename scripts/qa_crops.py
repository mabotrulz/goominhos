#!/usr/bin/env python3
"""Per-level QA crops: painted bg with boundary overlay, resized small for fast vision."""
from PIL import Image, ImageDraw
import json

levels = json.load(open('/home/hermes/goominhos/assets/levels.json'))
for lv in levels:
    im = Image.open(f'/tmp/goo_gen/bg{lv["id"]}.png').convert('RGB').resize((1600, 900))
    d = ImageDraw.Draw(im)
    for poly in lv['terrain']:
        d.line([tuple(p) for p in poly] + [tuple(poly[0])], fill=(255, 0, 0), width=6)
    px, py = lv['pipe'][0], lv['pipe'][1]
    d.ellipse([px - 40, py - 40, px + 40, py + 40], outline=(255, 0, 255), width=8)
    sx, sy = lv['spawn']
    d.ellipse([sx - 20, sy - 20, sx + 20, sy + 20], outline=(0, 0, 255), width=8)
    im.resize((900, 506)).save(f'/tmp/goo_qa_l{lv["id"]}.jpg', quality=82)
    print(f'/tmp/goo_qa_l{lv["id"]}.jpg')
