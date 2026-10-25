"""Render the counter artwork as a static GIF. No shell commands or remote assets."""
from io import BytesIO
from math import cos, sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path('/usr/share/fonts/TTF')

def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    for folder in (FONT_DIR, Path('/usr/share/fonts/truetype/dejavu')):
        if (folder / name).exists():
            return ImageFont.truetype(str(folder / name), size)
    return ImageFont.truetype(name, size)

THEMES = {
    'yellow': ('#ece9df', '#171917', '#f5cb32', '#fffacb'),
    'blue': ('#c9f3fa', '#163da5', '#ffed35', '#fffacb'),
    'purple': ('#ecd3ff', '#7826aa', '#64ffd0', '#fff2fb'),
}

def wrap(draw, text, face, width):
    lines, line = [], ''
    for word in text.split():
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=face) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = ''
            for char in word:
                if draw.textlength(line + char, font=face) > width:
                    lines.append(line)
                    line = ''
                line += char
    if line:
        lines.append(line)
    return lines

def fit_text(draw, text, box, max_size, bold=False, centered=False):
    x, y, width, height = box
    for size in range(max_size, 8, -1):
        face = font(size, bold)
        lines = wrap(draw, text, face, width)
        if len(lines) * (size + 7) <= height:
            break
    for line in lines:
        px = x + (width - draw.textlength(line, font=face)) / 2 if centered else x
        draw.text((px, y), line, font=face, fill='#151515')
        y += size + 7

def render_counter(config, fried=True):
    bg, edge, accent, paper = THEMES[config['theme']]
    im = Image.new('RGB', (1200, 720), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((25, 25, 1175, 695), outline=edge, width=10)
    d.rectangle((42, 42, 1158, 678), outline='white', width=3)
    title = config['unit'].upper() + ' SINCE KIKO'
    size = 48 if len(title) < 24 else 42
    for text, y in ((title, 65), ('SHAT HIMSELF', 128)):
        face = font(size, True)
        x = (1200 - d.textlength(text, font=face)) / 2
        for dx, dy, color in ((7, 7, '#151515'), (3, 3, 'white'), (0, 0, edge)):
            d.text((x + dx, y + dy), text, font=face, fill=color)
    d.rectangle((93, 253, 483, 593), fill=edge)
    d.rectangle((79, 239, 469, 579), fill='white', outline=edge, width=6)
    value = config['value']
    for size in range(280, 20, -1):
        face = font(size, True)
        if d.textlength(value, font=face) <= 354:
            break
    bounds = d.textbbox((0, 0), value, font=face)
    d.text((274 - d.textlength(value, font=face)/2, 409 - (bounds[3]-bounds[1])/2 - bounds[1]), value, font=face, fill=edge)
    d.rectangle((569, 276, 1111, 564), fill=edge)
    d.rectangle((555, 262, 1097, 550), fill=paper, outline='#151515', width=3)
    d.text((583, 287), 'TECHNICAL NOTE', font=font(23), fill=edge)
    fit_text(d, config['note'], (583, 337, 480, 155), 29)
    # Deliberately old-school clock and Word-style starburst.
    d.ellipse((420, 513, 552, 645), fill=edge, outline='#151515', width=3)
    d.ellipse((433, 526, 539, 632), fill='white', outline='#151515', width=2)
    d.line((486, 542, 486, 579, 515, 593), fill='#151515', width=6)
    d.ellipse((480, 573, 492, 585), fill='#ff3333')
    for cx, cy, radius in ((85, 125, 36), (1110, 100, 30), (1034, 590, 88)):
        points = []
        count = 12 if radius == 88 else 5
        for i in range(count*2):
            r = radius if i % 2 == 0 else radius * .64
            angle = i*pi/count - pi/2
            points.append((cx+r*cos(angle), cy+r*sin(angle)))
        d.polygon(points, fill=accent, outline=edge, width=3)
    fit_text(d, config['star'], (972, 563, 124, 66), 22, bold=True, centered=True)
    d.text((590, 624), 'STILL STATIC. OBVIOUSLY.', font=font(20), fill=edge)
    if fried:
        heavy, light = BytesIO(), BytesIO()
        im.resize((600, 360)).save(heavy, 'JPEG', quality=3, subsampling=2)
        im.save(light, 'JPEG', quality=12, subsampling=2)
        im = Image.open(BytesIO(heavy.getvalue())).resize((1200, 720), Image.Resampling.NEAREST).convert('RGB')
        im = im.quantize(colors=32).convert('RGB')
        readable = Image.open(BytesIO(light.getvalue()))
        im.paste(readable.crop((555, 262, 1098, 551)), (555, 262))
        # The configurable star note also needs to stay legible.
        im.paste(readable.crop((965, 557, 1103, 635)), (965, 557))
    output = BytesIO()
    im.save(output, 'GIF')
    return output.getvalue()
