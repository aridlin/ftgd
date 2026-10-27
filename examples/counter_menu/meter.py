"""URL-controlled meters. A reading never changes the saved template."""
from decimal import Decimal
from io import BytesIO
from math import cos, sin, pi
import re
from PIL import Image, ImageDraw
from render import THEMES, font, fit_text

STYLES = ('thermometer', 'ruler', 'progress')
DEFAULTS = dict(module='meter', meter_style='thermometer', minimum='0', maximum='100',
    mode='static', subject='horny meter', unit='%', value='75', theme='purple',
    note='An extremely scientific measurement. Change the number in the GIF URL to update it.',
    star='PEER REVIEWED')

def number(value):
    value = str(value)
    if not re.fullmatch(r'-?\d{1,12}(?:\.\d{1,6})?', value):
        raise ValueError('Use a number with up to 12 digits and 6 decimals')
    result = Decimal(value)
    return format(result.normalize(), 'f') if result else '0'

def reading(config, value):
    value = number(value)
    if not Decimal(config['minimum']) <= Decimal(value) <= Decimal(config['maximum']):
        raise ValueError('Meter value must be between its minimum and maximum')
    return dict(config, value=value)

def validate_meter(config):
    if set(config) != set(DEFAULTS): raise ValueError('Invalid meter fields')
    if config['meter_style'] not in STYLES: raise ValueError('Unknown meter style')
    if config['mode'] != 'static': raise ValueError('Meters use the value in their URL')
    config = dict(config, minimum=number(config['minimum']), maximum=number(config['maximum']))
    if Decimal(config['minimum']) >= Decimal(config['maximum']):
        raise ValueError('Meter maximum must be greater than its minimum')
    return reading(config, config['value'])

def meter_frame(config, phase=0):
    bg, edge, accent, paper = THEMES[config['theme']]
    image = Image.new('RGB', (1200, 720), bg)
    d = ImageDraw.Draw(image)
    d.rectangle((25,25,1175,695), outline=edge, width=10)
    d.rectangle((42,42,1158,678), outline='white', width=3)
    fit_text(d, config['subject'].upper(), (130,62,940,110), 49, bold=True, centered=True)
    lo, hi, value = (Decimal(config[k]) for k in ('minimum','maximum','value'))
    fraction = float((value-lo)/(hi-lo))
    colour = '#cf254e'
    d.rounded_rectangle((680,218,1110,565), radius=12, fill=paper, outline=edge, width=4)
    d.text((706,240), 'TECHNICAL NOTE', font=font(22,True), fill=edge)
    fit_text(d, config['note'], (706,284,378,163), 25)
    fit_text(d, config['star'], (706,476,378,60), 23, bold=True, centered=True)
    fit_text(d, config['value'] + (' ' + config['unit'] if config['unit'] else ''),
             (95,177,520,90), 67, bold=True, centered=True)
    style = config['meter_style']
    def label(text, x, y, align='left'):
        face=font(18,True)
        if align=='center': x-=d.textlength(text,font=face)/2
        if align=='right': x-=d.textlength(text,font=face)
        d.text((x,y),text,font=face,fill='#151515')
    def tick_label(index):
        return format((lo+(hi-lo)*Decimal(index)/10).normalize(),'f')
    if style=='thermometer':
        d.rounded_rectangle((220,290,300,585), radius=38, fill='white', outline=edge,width=5)
        top = 550-240*fraction
        if fraction: d.rectangle((240,top,280,579),fill=colour)
        d.ellipse((201,542,319,660),fill=colour,outline=edge,width=5)
        for i in range(11):
            y=550-24*i
            d.line((315,y,344 if i%5==0 else 332,y),fill=edge,width=3)
            if i%5==0: label(tick_label(i),356,y-12)
    else:
        x1,x2,y=104,606,404
        if style=='progress':
            d.rounded_rectangle((x1,y,x2,y+90),radius=12,fill='white',outline=edge,width=5)
            if fraction:
                d.rectangle((x1+7,y+7,x1+7+(x2-x1-14)*fraction,y+83),fill=colour)
            for i in range(1,10):
                x=x1+(x2-x1)*i/10
                d.line((x,y+7,x,y+83), fill=paper,width=3)
        else:
            d.rectangle((x1,y,x2,y+90),fill=accent,outline=edge,width=4)
            for i in range(51):
                x=x1+(x2-x1)*i/50
                d.line((x,y+4,x,y+(48 if i%5==0 else 25)),fill=edge,width=3)
            x=x1+(x2-x1)*fraction
            d.polygon(((x,y-5),(x-14,y-30),(x+14,y-30)),fill=colour)
            d.line((x,y+2,x,y+85),fill=colour,width=5)
        label(config['minimum'],x1,y+103)
        label(config['maximum'],x2,y+103,'right')
        label(f'{fraction*100:.1f}% OF RANGE',(x1+x2)/2,y+155,'center')
    # Only the corner sparkles move; the measurement remains exact in every frame.
    for cx,cy in ((86,110),(1112,110),(1100,624)):
        points=[]
        for i in range(10):
            angle=i*pi/5+phase*2*pi/5-pi/2
            r=26 if i%2==0 else 12
            points.append((cx+r*cos(angle),cy+r*sin(angle)))
        d.polygon(points,fill=accent,outline=edge,width=3)
    d.text((690,615),'VALUE SET BY THE URL.',font=font(18,True),fill=edge)
    return image

def render_meter(config, animated=False):
    base=meter_frame(config)
    frames=[base]
    if animated:
        for i in range(1,8):
            moved=meter_frame(config,i/8)
            frame=base.copy()
            for box in ((55,79,118,142),(1080,79,1144,142),(1068,592,1132,656)):
                frame.paste(moved.crop(box),box[:2])
            frames.append(frame)
    palette=base.quantize(colors=64,dither=Image.Dither.NONE)
    frames=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    output=BytesIO()
    frames[0].save(output,'GIF',save_all=animated,append_images=frames[1:],duration=150,
                   loop=0,disposal=1,optimize=True)
    return output.getvalue()
