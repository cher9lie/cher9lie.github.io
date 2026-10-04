"""Render authentic short PDF excerpts, with red boxes added outside the text."""
from pathlib import Path
import json, pdfplumber, pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'src/content/blog/flaash-atmospheric-correction-concepts'
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(FONT,n)
def excerpt(name,num,regions,title,filename):
    path=ROOT/'cache'/(name+'.pdf')
    doc=pdfium.PdfDocument(path)
    image=doc[num-1].render(scale=3).to_pil().convert('RGB')
    pieces=[]
    for label,box in regions:
        crop=image.crop(tuple(round(v*3) for v in box))
        if crop.width>1050:
            crop=crop.resize((1050,round(crop.height*1050/crop.width)))
        pieces.append((label,crop))
    height=130+sum(76+c.height for _,c in pieces)+50
    canvas=Image.new('RGB',(1200,height),'#f4f6fa');d=ImageDraw.Draw(canvas)
    d.text((48,28),title,font=font(28),fill='#17243c')
    d.text((48,75),f'原 PDF 局部摘图 · 第 {num} 页 · 红框为本文标注',font=font(20),fill='#596477')
    y=135
    for label,crop in pieces:
        d.text((48,y),label,font=font(22),fill='#17243c');y+=38
        canvas.paste(crop,(60,y));d.rectangle((54,y-6,66+crop.width,y+crop.height+6),outline='#c93434',width=3)
        y+=crop.height+38
    canvas.save(OUT/filename)
    return {'file':filename,'source':name,'pdf_page':num,'regions':regions,'method':'original PDF rendering, cropped excerpts, red outlines; original words unchanged'}
specs=[]
def region(name,num,label,pattern,last=False):
    with pdfplumber.open(ROOT/'cache'/(name+'.pdf')) as p:
        hits=p.pages[num-1].search(pattern)
        h=hits[-1] if last else hits[0]
        return (label,(h['x0']-0.5,h['top']-1,h['x1']+0.5,h['bottom']+1))
specs.append(excerpt('envi-flaash',20,[
 region('envi-flaash',20,'卫星高度：km',r'Sensor Altitude \(km\)',True),
 region('envi-flaash',20,'平均地面高程：km',r'Ground Elevation \(km\)'),
 region('envi-flaash',20,'像元大小：m',r'Pixel Size \(m\)'),
], 'ENVI 大气校正手册：三个字段的单位不同', 'manual-flaash-units.png'))
specs.append(excerpt('envi-flaash',12,[
 region('envi-flaash',12,'旧手册列出的格式：BIL 或 BIP',r'interleaved-by-line \(BIL\) or band-interleaved-by-pixel \(BIP\) format\.'),
], 'ENVI 旧版手册：并非只能使用 BIL', 'manual-flaash-interleave.png'))
specs.append(excerpt('s2-psd',397,[
 region('s2-psd',397,'L1C 像元的物理意义：大气顶反射率',r'provided in Top[\s\S]*?radiances\.'),
 region('s2-psd',397,'解码涉及比例系数和偏移量；括号解释见正文',r'Reflectance \(float\) = DN \+ RADIO_ADD_OFFSET / \(QUANTIFICATION_VALUE\)')
], 'Sentinel-2 产品规范 15.0：L1C 的定义', 'manual-sentinel-l1c.png'))
specs.append(excerpt('s2-l2a',13,[
 region('s2-l2a',13,'L2A 提供地表（BOA）反射率',r'surface \(BOA\) reflectance'),
 region('s2-l2a',13,'排除 B10 的理由：它不提供地表信息',r'1375 nm cirrus band B10, as it does not contain surface\s+information\.')
], 'Sentinel-2 L2A 产品定义 4.9：BOA 与 B10', 'manual-sentinel-l2a.png'))
(ROOT/'figure-sources.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2),encoding='utf-8')

# Deterministic conceptual diagram, separate from measurements and document excerpts.
im=Image.new('RGB',(1500,820),'#f7f9fc');d=ImageDraw.Draw(im)
d.text((55,35),'Sentinel-2：两条不同的数据处理路线',font=font(38),fill='#1f304a')
d.text((55,92),'L1C 和 L2A 的整数编码看起来相似，代表的物理量却不同。',font=font(25),fill='#58667a')
boxes=[(60,185,455,335,'L1C · 大气顶反射率','SAFE / JP2 整数编码','#e2eafb'),(550,185,940,335,'恢复大气顶辐亮度','元数据 + 太阳几何 + 单位','#e2eafb'),(1035,185,1440,335,'FLAASH','辐射传输模型 → 地表反射率','#e2eafb'),(60,500,455,650,'L2A · 地表反射率','官方已完成大气校正','#e0f0e7'),(550,500,940,650,'解码 + 质量筛选','scale / offset + SCL','#e0f0e7'),(1035,500,1440,650,'指数、时间序列、反演','仍需考虑地形与观测方向','#e0f0e7')]
for x0,y0,x1,y1,t1,t2,c in boxes:
 d.rounded_rectangle((x0,y0,x1,y1),radius=18,fill=c,outline='#b5c4d8',width=2)
 d.text((x0+20,y0+30),t1,font=font(28),fill='#1f304a')
 d.text((x0+20,y0+82),t2,font=font(20),fill='#455773')
for y in [260,575]:
 for x in [455,940]:
  d.line((x+8,y,x+83,y),fill='#496c94',width=5);d.polygon([(x+83,y),(x+68,y-9),(x+68,y+9)],fill='#496c94')
d.text((70,382),'上：需要自己控制大气模型时使用；确认辐亮度后再进入 FLAASH。',font=font(25),fill='#496c94')
d.text((70,698),'下：常规分析可直接使用；地表反射率不应重复送进 FLAASH。',font=font(25),fill='#38745a')
d.text((70,759),'教学流程图；未表示所有软件内部步骤，不是实测数据。',font=font(20),fill='#6b778b')
im.save(OUT/'processing-chain.png')
print('rendered',len(specs),'manual excerpts + processing chain')
