"""Render the counter artwork as a static GIF. No shell commands or remote assets."""
from io import BytesIO
from functools import lru_cache
from threading import BoundedSemaphore
RENDER_SLOTS = BoundedSemaphore(2)
from math import cos, sin, pi
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path('/usr/share/fonts/TTF')

@lru_cache(maxsize=128)
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

def counter_frame(config, fried=True, phase=0):
    bg, edge, accent, paper = THEMES[config['theme']]
    im = Image.new('RGB', (1200, 720), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((25, 25, 1175, 695), outline=edge, width=10)
    d.rectangle((42, 42, 1158, 678), outline='white', width=3)
    title = config['unit'].upper() + ' SINCE ' + config.get('subject', 'kiko shat himself').upper()
    for size in range(48, 16, -1):
        face = font(size, True)
        title_lines = wrap(d, title, face, 940)
        if len(title_lines) * (size + 8) <= 145:
            break
    y = 60
    for text in title_lines:
        x = (1200 - d.textlength(text, font=face)) / 2
        for dx, dy, color in ((7, 7, '#151515'), (3, 3, 'white'), (0, 0, edge)):
            d.text((x + dx, y + dy), text, font=face, fill=color)
        y += size + 8
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
    angle = phase * 2*pi - pi/2
    d.line((486+37*cos(angle),579+37*sin(angle),486,579,486+29*cos(angle/12+.5),579+29*sin(angle/12+.5)), fill='#151515', width=6)
    d.ellipse((480, 573, 492, 585), fill='#ff3333')
    for cx, cy, radius in ((85, 125, 36), (1110, 100, 30), (1034, 590, 88)):
        points = []
        count = 12 if radius == 88 else 5
        for i in range(count*2):
            r = radius if i % 2 == 0 else radius * .64
            angle = i*pi/count - pi/2 + (phase*2*pi/5 if radius != 88 else .07*sin(phase*2*pi))
            points.append((cx+r*cos(angle), cy+r*sin(angle)))
        d.polygon(points, fill=accent, outline=edge, width=3)
    fit_text(d, config['star'], (972, 563, 124, 66), 22, bold=True, centered=True)
    caption = 'COUNTING. REFRESH FOR THE LATEST.' if config.get('mode') == 'counting' else 'STILL STATIC. OBVIOUSLY.'
    d.text((590, 624), caption, font=font(18), fill=edge)
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
    return im

def render_counter(config, fried=True, animated=False):
    with RENDER_SLOTS:
        return _render_counter(config, fried, animated)

def _render_counter(config, fried=True, animated=False):
    base = counter_frame(config, fried, 0)
    frames = [base]
    if animated:
        for i in range(1,12):
            moved = counter_frame(config, fried, i/12)
            frame = base.copy()
            for box in ((40,80,130,170),(1070,60,1150,140),(418,510,555,648),(943,499,1125,685)):
                frame.paste(moved.crop(box),box[:2])
            frames.append(frame)
    palette = base.quantize(colors=64, dither=Image.Dither.NONE)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    output = BytesIO()
    frames[0].save(output, 'GIF', save_all=animated, append_images=frames[1:],
                   duration=250, loop=0, disposal=1, optimize=True)
    return output.getvalue()

def render_menu_image(lines):
    """Landscape cards use Discord's limited preview height efficiently."""
    width, margin, gap = 1600, 28, 22
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    body, command, heading = font(26), font(29, True), font(28, True)
    title = next(text for kind, text in lines if kind == 'H')
    groups, intro, footer = [], [], ''
    for kind, text in lines:
        if kind == 'H':
            continue
        if kind == 'F':
            footer = text
        elif kind == 'P':
            groups.append([text, []])
        elif groups:
            groups[-1][1].append((kind, text))
        else:
            intro.append(text)
    if not groups:
        groups = [['MENU', []]]
    count = len(groups)
    column_width = (width-2*margin-gap*(count-1))//count
    inner = column_width-32
    header_rows = wrap(measure, ' • '.join(intro), body, width-2*margin)
    top = 88 + 34*len(header_rows)
    columns = []
    for label, items in groups:
        blocks, height = [], 56
        for kind, text in items:
            if kind == 'I':
                h = int(inner*.6)+14
                blocks.append(('I', text, h))
            elif text.startswith('s/'):
                cmd, _, caption = text.partition('  ')
                inline = bool(caption) and measure.textlength(cmd,font=command) < 150
                captions = wrap(measure, caption, body, inner-180 if inline else inner-24) if caption else []
                commands = wrap(measure, cmd, command, inner-24)
                h = 22 + (max(36,32*len(captions)) if inline else 32*len(captions)+36*len(commands))
                blocks.append(('C', (captions, commands, inline), h))
            else:
                rows = wrap(measure, text, body, inner)
                h = 32*len(rows)+12
                blocks.append(('T', rows, h))
            height += h
        columns.append((label, blocks, height))
    content_height = max(h for _,_,h in columns)
    height = top+content_height+64
    im = Image.new('RGB', (width,height), '#0c1018')
    d = ImageDraw.Draw(im)
    d.text((margin,20), title, font=font(38,True), fill='white')
    for i,row in enumerate(header_rows):
        d.text((margin,75+34*i), row, font=body, fill='#edf2fc')
    for col,(label,blocks,_) in enumerate(columns):
        x = margin+col*(column_width+gap)
        d.rectangle((x,top,x+column_width,top+content_height),fill='#141e2e')
        d.text((x+16,top+12),label,font=heading,fill='white')
        y=top+56
        for kind,text,h in blocks:
            if kind=='I':
                with Image.open(BytesIO(render_counter(json.loads(text)))) as preview:
                    im.paste(preview.convert('RGB').resize((inner,int(inner*.6)),Image.Resampling.LANCZOS),(x+16,y))
            elif kind=='C':
                captions,commands,inline=text
                d.rectangle((x+16,y,x+column_width-16,y+h-10),fill='#24364e')
                cy=y+7
                for row in captions:
                    d.text((x+28+(156 if inline else 0),cy),row,font=body,fill='white');cy+=32
                if inline:
                    cy=y+7
                for row in commands:
                    d.text((x+28,cy),row,font=command,fill='#ffe477');cy+=36
            else:
                for i,row in enumerate(text):
                    d.text((x+16,y+32*i),row,font=body,fill='#edf2fc')
            y+=h
    d.text((margin,height-41),footer,font=font(23),fill='#edf2fc')
    return im
