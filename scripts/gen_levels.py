#!/usr/bin/env python3
"""Goominhos level pipeline.

One geometry dict per level is the single source of truth:
  - levels/levelN.svg      -> canonical boundary document (what Mario asked: SVG-first)
  - /tmp/goo_gen/levelN.png -> flat-color render of that SVG data (paint blueprint)
  - painted via gemini-3.1-flash-image (reference-following) -> assets/bgN.jpg
  - assets/levels.js       -> boundary polylines + spawn/pipe/goo data for the engine

Boundary extraction = the same polylines we draw into the SVG (no parsing needed).
"""
import base64, json, math, os, time, urllib.request

env = {}
for line in open(os.path.expanduser('~/.hermes/.env')):
    if '=' in line:
        k, v = line.strip().split('=', 1); env[k] = v
GEMINI_KEY = env.get('GEMINI_API_KEY')
W, H = 1600, 900
OUT_TMP = '/tmp/goo_gen'; os.makedirs(OUT_TMP, exist_ok=True)
ASSETS = '/home/hermes/goominhos/assets'; os.makedirs(ASSETS, exist_ok=True)
LEVELS = '/home/hermes/goominhos/levels'; os.makedirs(LEVELS, exist_ok=True)

# ---------------------------------------------------------------- level data
# terrain: list of polylines [[x,y],...] (solid ground BELOW/OUTSIDE the line)
# decor: flat shapes the painter will turn into scenery (never boundaries)
LEVELS_DATA = [
 dict(id=1, name='A Ponte', intro='Os Goominhos querem chegar ao cano! Arrasta-os e constrói uma ponte sobre o desfiladeiro!',
      goos=dict(basic=14), target=4, spawn=[300, 540], pipe=[1330, 545, 'down'],
      terrain=[[[0, 620], [550, 620], [560, 900], [0, 900]],
               [[1050, 600], [1600, 600], [1600, 900], [1040, 900]]],
      decor=[('sun', [170, 140, 70]), ('cloud', [620, 150, 90]), ('cloud', [1250, 110, 70]),
             ('flowers', [220, 620]), ('flowers', [420, 620]), ('flowers', [1200, 600]), ('flowers', [1460, 600]),
             ('river', [800, 880])],
      paint='a deep canyon between two grassy cliff plateaus, a tiny river at the bottom'),
 dict(id=2, name='A Torre', intro='O cano está lá no céu! Constrói uma torre bem alta com os Goominhos!',
      goos=dict(basic=16), target=5, spawn=[700, 700], pipe=[800, 190, 'down'],
      terrain=[[[0, 800], [1600, 800], [1600, 900], [0, 900]]],
      decor=[('sun', [1400, 120, 80]), ('cloud', [300, 180, 100]), ('cloud', [800, 120, 80]),
             ('cloud', [1200, 240, 70]), ('flowers', [200, 800]), ('flowers', [1400, 800]),
             ('tree', [1450, 800]), ('birds', [500, 250])],
      paint='a wide sunny meadow under a big blue sky, a pipe hanging from a small cloud high above'),
 dict(id=3, name='Os Levinhos', intro='Estes Goominhos são Levinhos — flutuam como balões! Usa-os para subir até ao penhasco!',
      goos=dict(basic=8, balloon=6), target=5, spawn=[420, 720], pipe=[1180, 150, 'left'],
      terrain=[[[0, 800], [1600, 800], [1600, 900], [0, 900]],
               [[1250, 60], [1600, 60], [1600, 800], [1250, 800]]],
      decor=[('sun', [200, 130, 70]), ('cloud', [700, 130, 80]), ('vine', [1250, 400]),
             ('flowers', [300, 800]), ('flowers', [900, 800]), ('birds', [950, 200])],
      paint='a tall rocky cliff with vines on the right side of a green meadow'),
 dict(id=4, name='A Curva', intro='O cano está escondido debaixo da rocha! Os Pesadões são muito pesados — usa-os para dobrar a estrutura para baixo!',
      goos=dict(basic=8, heavy=5), target=4, spawn=[250, 220], pipe=[1150, 660, 'up'],
      terrain=[[[0, 300], [450, 300], [450, 900], [0, 900]],
               [[750, 380], [1600, 380], [1600, 470], [750, 470]],
               [[0, 850], [1600, 850], [1600, 900], [0, 900]]],
      decor=[('cloud', [250, 100, 70]), ('vine', [1100, 470]), ('flowers', [180, 300]),
             ('mushroom', [600, 850]), ('mushroom', [1400, 850]), ('crystals', [900, 850])],
      paint='a rocky overhang shelf floating over a cave floor with mushrooms and glowing crystals'),
 dict(id=5, name='O Túnel', intro='Os Colas agarram-se às paredes! Sobe pelo túnel, parede a parede, até ao cano lá em cima!',
      goos=dict(basic=4, sticky=10), target=5, spawn=[300, 740], pipe=[1000, 210, 'down'],
      terrain=[[[0, 820], [1600, 820], [1600, 900], [0, 900]],
               [[820, 150], [900, 150], [900, 820], [820, 820]],
               [[1100, 150], [1180, 150], [1180, 820], [1100, 820]]],
      decor=[('crystals', [860, 700]), ('crystals', [1140, 500]), ('mushroom', [200, 820]),
             ('mushroom', [1400, 820]), ('vine', [900, 300]), ('cloud', [300, 120, 70])],
      paint='a deep crystal cave with a narrow vertical tunnel between two rock walls'),
 dict(id=6, name='O Vendaval', intro='Cuidado — o vento sopra com força! Mistura Pesadões, Levinhos e Goominhos para aguentar a ponte no vendaval!',
      goos=dict(basic=6, heavy=4, balloon=3), target=5, spawn=[280, 560], pipe=[1420, 555, 'down'],
      wind=dict(x0=600, x1=1250, y0=0, y1=900, fx=-0.0002),
      terrain=[[[0, 640], [600, 640], [610, 900], [0, 900]],
               [[1240, 630], [1600, 630], [1600, 900], [1230, 900]]],
      decor=[('cloud', [200, 130, 70]), ('cloud', [900, 100, 90]), ('birds', [1000, 300]),
             ('flowers', [200, 640]), ('flowers', [1450, 630]), ('tree', [100, 640])],
      paint='two grassy cliff plateaus over a canyon, wind lines and leaves blowing through the air'),
]

# ---------------------------------------------------------------- SVG emit
PALETTE = dict(ground='#7a9b4d', rock='#8d7b68', sky='#bfe3f2', sun='#ffd54f', cloud='#ffffff')
def svg_for(lv):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{PALETTE["sky"]}"/>']
    for poly in lv['terrain']:
        pts = ' '.join(f'{x},{y}' for x, y in poly)
        parts.append(f'<polygon class="boundary" points="{pts}" fill="{PALETTE["ground"]}" stroke="#5b7a36" stroke-width="6"/>')
    for kind, d in lv['decor']:
        if kind == 'sun':
            parts.append(f'<circle cx="{d[0]}" cy="{d[1]}" r="{d[2]}" fill="{PALETTE["sun"]}"/>')
        elif kind == 'cloud':
            x, y, r = d
            parts.append(f'<g fill="{PALETTE["cloud"]}"><ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r*0.55}"/><ellipse cx="{x-r*0.7}" cy="{y+r*0.2}" rx="{r*0.6}" ry="{r*0.4}"/><ellipse cx="{x+r*0.7}" cy="{y+r*0.2}" rx="{r*0.6}" ry="{r*0.4}"/></g>')
        elif kind == 'flowers':
            parts.append(f'<circle cx="{d[0]}" cy="{d[1]-14}" r="12" fill="#ff8a80"/><circle cx="{d[0]+26}" cy="{d[1]-10}" r="10" fill="#f48fb1"/>')
        elif kind == 'tree':
            parts.append(f'<rect x="{d[0]-12}" y="{d[1]-110}" width="24" height="110" fill="#6d4a21"/><circle cx="{d[0]}" cy="{d[1]-140}" r="60" fill="#4caf50"/>')
        elif kind == 'vine':
            parts.append(f'<path d="M{d[0]},{d[1]-100} q20,60 -10,120 q-20,50 5,100" stroke="#4caf50" stroke-width="10" fill="none"/>')
        elif kind == 'river':
            parts.append(f'<rect x="0" y="{d[1]-16}" width="{W}" height="32" fill="#64b5f6"/>')
        elif kind == 'birds':
            parts.append(f'<path d="M{d[0]},{d[1]} q12,-14 24,0 q12,-14 24,0 M{d[0]+70},{d[1]+30} q10,-12 20,0 q10,-12 20,0" stroke="#455a64" stroke-width="5" fill="none"/>')
        elif kind == 'mushroom':
            parts.append(f'<rect x="{d[0]-8}" y="{d[1]-26}" width="16" height="26" fill="#fff3e0"/><circle cx="{d[0]}" cy="{d[1]-30}" r="22" fill="#e57373"/>')
        elif kind == 'crystals':
            parts.append(f'<polygon points="{d[0]},{d[1]-50} {d[0]+18},{d[1]} {d[0]-18},{d[1]}" fill="#b39ddb"/><polygon points="{d[0]+30},{d[1]-34} {d[0]+44},{d[1]} {d[0]+16},{d[1]}" fill="#9575cd"/>')
    px, py, pd = lv['pipe']
    parts.append(f'<circle class="pipe" cx="{px}" cy="{py}" r="34" fill="#37474f" stroke="#263238" stroke-width="8"/>')
    parts.append(f'<circle class="spawn" cx="{lv["spawn"][0]}" cy="{lv["spawn"][1]}" r="10" fill="#e91e63"/>')
    parts.append('</svg>')
    return '\n'.join(parts)

# ---------------------------------------------------------------- flat render (PIL, same data)
def flat_png(lv, path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (W, H), PALETTE['sky']); d = ImageDraw.Draw(im)
    for poly in lv['terrain']:
        d.polygon([tuple(p) for p in poly], fill=PALETTE['ground'], outline='#5b7a36', width=6)
    for kind, dd in lv['decor']:
        if kind == 'sun': d.ellipse([dd[0]-dd[2], dd[1]-dd[2], dd[0]+dd[2], dd[1]+dd[2]], fill=PALETTE['sun'])
        elif kind == 'cloud':
            x, y, r = dd
            d.ellipse([x-r, y-r*0.55, x+r, y+r*0.55], fill='#ffffff')
            d.ellipse([x-r*1.3, y-r*0.2, x-r*0.1, y+r*0.6], fill='#ffffff')
            d.ellipse([x+r*0.1, y-r*0.2, x+r*1.3, y+r*0.6], fill='#ffffff')
        elif kind == 'flowers':
            d.ellipse([dd[0]-12, dd[1]-26, dd[0]+12, dd[1]-2], fill='#ff8a80')
            d.ellipse([dd[0]+16, dd[1]-20, dd[0]+36, dd[1]], fill='#f48fb1')
        elif kind == 'tree':
            d.rectangle([dd[0]-12, dd[1]-110, dd[0]+12, dd[1]], fill='#6d4a21')
            d.ellipse([dd[0]-60, dd[1]-200, dd[0]+60, dd[1]-80], fill='#4caf50')
        elif kind == 'vine': d.line([dd[0], dd[1]-100, dd[0]+20, dd[1]-40, dd[0]-10, dd[1]+20, dd[0]+5, dd[1]+100], fill='#4caf50', width=10)
        elif kind == 'river': d.rectangle([0, dd[1]-16, W, dd[1]+16], fill='#64b5f6')
        elif kind == 'birds': d.arc([dd[0], dd[1]-14, dd[0]+48, dd[1]+14], 200, 340, fill='#455a64', width=5)
        elif kind == 'mushroom':
            d.rectangle([dd[0]-8, dd[1]-26, dd[0]+8, dd[1]], fill='#fff3e0')
            d.ellipse([dd[0]-22, dd[1]-52, dd[0]+22, dd[1]-8], fill='#e57373')
        elif kind == 'crystals':
            d.polygon([(dd[0], dd[1]-50), (dd[0]+18, dd[1]), (dd[0]-18, dd[1])], fill='#b39ddb')
            d.polygon([(dd[0]+30, dd[1]-34), (dd[0]+44, dd[1]), (dd[0]+16, dd[1])], fill='#9575cd')
    px, py, _ = lv['pipe']
    d.ellipse([px-34, py-34, px+34, py+34], fill='#37474f', outline='#263238', width=8)
    im.save(path)

# ---------------------------------------------------------------- gemini paint
def gemini_paint(lv, flat_path, out_png):
    prompt = (
        'Use this flat-color sketch as an EXACT blueprint. Repaint it as a rich, beautiful children\'s book '
        'gouache landscape with soft textured brushstrokes and warm saturated colors. CRITICAL: keep every shape, '
        'position and proportion identical — the green flat shapes become painted terrain exactly where they are '
        f'({lv["paint"]}), the sky stays open, the white blobs become fluffy clouds exactly in place, the yellow '
        'circle becomes a glowing sun, small shapes become their matching painted details (flowers, trees, vines, '
        'mushrooms, crystals, birds, river). The dark circle becomes a dark metal pipe opening of the same size in '
        'the same place. Do NOT add new objects, do NOT move anything, no characters, no text, no letters.')
    img_b64 = base64.b64encode(open(flat_path, 'rb').read()).decode()
    body = {'contents': [{'parts': [
        {'text': prompt},
        {'inline_data': {'mime_type': 'image/png', 'data': img_b64}}]}],
        'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']}}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={GEMINI_KEY}'
    for a in range(4):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=240).read())
            for cand in d.get('candidates', []):
                for part in cand.get('content', {}).get('parts', []):
                    if 'inlineData' in part or 'inline_data' in part:
                        data = (part.get('inlineData') or part.get('inline_data'))['data']
                        open(out_png, 'wb').write(base64.b64decode(data))
                        print('PAINTED', os.path.basename(out_png)); return True
            print('no image in response', d.get('promptFeedback'))
        except Exception as e:
            print('retry', a, type(e).__name__, str(e)[:120]); time.sleep(8 * a + 4)
    print('PAINT FAIL', lv['id']); return False

# ---------------------------------------------------------------- run
levels_js = []
for lv in LEVELS_DATA:
    svg = svg_for(lv)
    open(f'{LEVELS}/level{lv["id"]}.svg', 'w').write(svg)
    flat = f'{OUT_TMP}/flat{lv["id"]}.png'
    flat_png(lv, flat)
    painted = f'{OUT_TMP}/bg{lv["id"]}.png'
    if not os.path.exists(painted):
        gemini_paint(lv, flat, painted)
    levels_js.append(dict(id=lv['id'], name=lv['name'], intro=lv['intro'], goos=lv['goos'],
                          target=lv['target'], spawn=lv['spawn'], pipe=lv['pipe'],
                          terrain=lv['terrain'], wind=lv.get('wind')))

open(f'{ASSETS}/levels.json', 'w').write(json.dumps(levels_js, ensure_ascii=False))
print('levels.json written,', len(levels_js), 'levels')
print('ALL DONE')
