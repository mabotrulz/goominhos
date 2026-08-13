#!/usr/bin/env python3
"""Portfolio icon: goo face drawn over a bg1 canyon crop."""
from PIL import Image, ImageDraw

bg = Image.open('/home/hermes/goominhos/assets/bg1.jpg').convert('RGB')
S = 512
bg = bg.resize((S * 2, S), Image.LANCZOS).crop((0, 0, S, S))  # left-cliff area
im = Image.new('RGB', (S, S)); im.paste(bg, (0, 0))
d = ImageDraw.Draw(im)
# goo body
cx, cy, r = S // 2, int(S * 0.58), 150
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#7ed957', outline='#3e8e2f', width=10)
# shine
d.ellipse([cx - r * 0.62, cy - r * 0.62, cx - r * 0.1, cy - r * 0.28], fill='#c9f4ae')
# eyes
for ex in (-55, 55):
    d.ellipse([cx + ex - 38, cy - 70, cx + ex + 38, cy + 6], fill='#ffffff', outline='#2c5e20', width=5)
    d.ellipse([cx + ex - 14, cy - 46, cx + ex + 14, cy - 18], fill='#222222')
# smile
d.arc([cx - 55, cy + 8, cx + 55, cy + 90], 20, 160, fill='#2c5e20', width=10)
im.save('/home/hermes/portfolio/goominhos_icon.png')
print('icon saved')
