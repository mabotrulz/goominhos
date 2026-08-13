#!/usr/bin/env python3
"""QA sheet: painted bg with red boundary overlay (left) vs flat blueprint (right), per level."""
from PIL import Image, ImageDraw
import json

levels = json.load(open('/home/hermes/goominhos/assets/levels.json'))

def overlay(lv):
    im = Image.open(f'/tmp/goo_gen/bg{lv["id"]}.png').convert('RGB').resize((1600, 900))
    d = ImageDraw.Draw(im)
    for poly in lv['terrain']:
        d.line([tuple(p) for p in poly] + [tuple(poly[0])], fill=(255, 0, 0), width=5)
    px, py = lv['pipe'][0], lv['pipe'][1]
    d.ellipse([px - 40, py - 40, px + 40, py + 40], outline=(255, 0, 255), width=6)
    sx, sy = lv['spawn']
    d.ellipse([sx - 20, sy - 20, sx + 20, sy + 20], outline=(0, 0, 255), width=6)
    return im

for group, out in [([0, 1, 2], '/tmp/goo_qa1.jpg'), ([3, 4, 5], '/tmp/goo_qa2.jpg')]:
    tw = 780; th = int(tw * 9 / 16)
    sheet = Image.new('RGB', (tw * 2 + 18, th * 3 + 24), (20, 20, 30))
    d = ImageDraw.Draw(sheet)
    for i, idx in enumerate(group):
        lv = levels[idx]
        sheet.paste(overlay(lv).resize((tw, th)), (0, i * (th + 8)))
        flat = Image.open(f'/tmp/goo_gen/flat{lv["id"]}.png').resize((tw, th))
        sheet.paste(flat, (tw + 10, i * (th + 8)))
        d.text((6, i * (th + 8) + 4), f'level {idx + 1} painted+overlay | flat', fill=(255, 255, 0))
    sheet.save(out, quality=87)
    print(out)
