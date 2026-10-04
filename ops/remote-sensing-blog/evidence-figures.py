"""Reproducible original-document excerpts. Coordinates are PDF points, not OCR images.

No source text is typeset anew: PDFium renders the downloaded original page;
Pillow only crops, composes, labels outside the excerpt, and adds red rectangles.
"""
from pathlib import Path
import hashlib
import json
import re
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'src/content/blog/flaash-atmospheric-correction-concepts'
FONT = 'C:/Windows/Fonts/msyh.ttc'
SCALE = 3
WIDTH = 1320
manuals = {m['name']: m for m in json.loads((ROOT/'evidence-manuals.json').read_text(encoding='utf-8'))}
manuals.update({
 's2-psd': {'url':'https://sentinels.copernicus.eu/documents/d/sentinel/s2-pdgs-cs-di-psd-v15-0'},
 's2-l2a': {'url':'https://step.esa.int/thirdparties/sen2cor/2.10.0/docs/S2-PDGS-MPC-L2A-PDD-V14.9-v4.9.pdf'},
 'envi-flaash': {'url':'https://www.nv5geospatialsoftware.com/portals/0/pdfs/envi/QUAC_FLAASH_Module.pdf'},
})
TITLES = {
 's2-handbook':'ESA · Sentinel-2 User Handbook · 2015',
 's2-psd':'ESA · Sentinel-2 产品规范 15.0 · 2024',
 's2-l2a':'ESA · L2A 产品定义 4.9 · 2021',
 'sen2cor-atbd':'ESA · Sen2Cor L2A ATBD 2.10 · 2021',
 'ccrs-fundamentals':'加拿大遥感中心 CCRS · Fundamentals of Remote Sensing',
 'nist-radiometry':'NIST · Handbook 152 · 辐射度量',
 'nist-brdf':'NBS/NIST · Monograph 160 · 1977',
 'modis-vi':'NASA · MODIS 植被指数 ATBD 3 · 1999',
 'modis-atmosphere':'NASA · MODIS 大气校正 ATBD 4.0 · 1999',
 'modis-temperature':'NASA · MODIS 地表温度 ATBD 3.3 · 1999',
 'ocean-protocols':'NASA · Ocean Optics Protocols · Rev. 4 · Vol. I · 2003',
 'landsat-handbook':'USGS · Landsat 8 手册 · LSDS-1574 v5.0',
 'landsat-c2':'USGS · Collection 2 L2 指南 · LSDS-1619 v6.0',
 'envi-flaash':'ITT/ENVI · QUAC–FLAASH 手册 4.7 · 2009',
 'ogc-cog':'© 2023 OGC · Cloud Optimized GeoTIFF 1.0',
}
plumbers = {}
pdfs = {}

def page(name, num):
 if name not in plumbers:
  plumbers[name] = pdfplumber.open(ROOT/'cache'/(name+'.pdf'))
 return plumbers[name].pages[num-1]

def reg(name, num, label, box, highlights=None):
 return {'source':name, 'pdf_page':num, 'label':label, 'box':box, 'highlights':highlights or []}

def hit(name, num, label, pattern, pad=3):
 hits = page(name,num).search(pattern, flags=re.I)
 if not hits:
  print('MISSING',name,num,pattern)
  return reg(name,num,label,[0,0,10,10],['MISSING'])
 h = hits[0]
 # Include complete original lines: a match can start or finish mid-line.
 # Cropping just its character bounds can clip neighbouring words/glyphs.
 all_lines = page(name,num).extract_text_lines()
 lines = [line for line in all_lines
          if line['bottom'] > h['top'] and line['top'] < h['bottom']]
 top = min(line['top'] for line in lines)
 bottom = max(line['bottom'] for line in lines)
 before = [line['bottom'] for line in all_lines if line['bottom'] <= top]
 after = [line['top'] for line in all_lines if line['top'] >= bottom]
 # Do not include fragments of the preceding/following line in the padding.
 crop_top = max(top-pad, (top+max(before))/2 if before else 0)
 crop_bottom = min(bottom+pad, (bottom+min(after))/2 if after else page(name,num).height)
 return reg(name,num,label,[min(line['x0'] for line in lines)-pad,
                           crop_top,
                           max(line['x1'] for line in lines)+pad,
                           crop_bottom])

cards = []
def card(code, title, *regions):
 cards.append({'id':code, 'title':title, 'file':f'evidence-{code}.png', 'regions':list(regions)})

card('01','遥感、被动／主动观测与电磁波',
 hit('ccrs-fundamentals',5,'遥感：不接触地表，记录反射或发射能量',r'acquiring\s+information[\s\S]*?emitted energy'),
 hit('ccrs-fundamentals',19,'被动观测：利用自然存在的能量',r'Remote sensing systems which[\s\S]*?passive sensors'),
 hit('ccrs-fundamentals',19,'主动观测：仪器提供照明能量',r'Active sensors[\s\S]*?illumination'),
 hit('ccrs-fundamentals',8,'波长：相邻波峰之间的距离',r'The wavelength[\s\S]*?successive wave crests'))
card('02','像元、空间分辨率与采样不能混为一谈',
 hit('ccrs-fundamentals',20,'栅格：数字图像的行、列和像元',r'digital format[\s\S]*?pixels'),
 hit('ccrs-fundamentals',39,'IFOV：传感器的瞬时角视场',r'The IFOV is[\s\S]*?time \(B\)'),
 hit('ccrs-fundamentals',39,'像元间距与空间分辨率并非可互换的词',r'pixel size[\s\S]*?interchangeable'))
card('03','四种分辨率中的光谱、辐射与时间',
 hit('ccrs-fundamentals',41,'光谱分辨率：区分精细波长区间',r'Spectral\s+resolution describes[\s\S]*?wavelength intervals'),
 hit('ccrs-fundamentals',43,'8 位量化的例子：256 个等级，数值为 0–255',r'8 bits[\s\S]*?0 to 255'),
 hit('ccrs-fundamentals',42,'高光谱的特征：大量很窄的光谱波段',r'hyperspectral sensors[\s\S]*?electromagnetic spectrum'),
 hit('ccrs-fundamentals',44,'实际时间采样还取决于传感器能力、扫描覆盖和纬度',r'actual temporal resolution[\s\S]*?latitude'))
card('04','MSI 的 12 位量化、辐射准确度与 SNR',
 reg('s2-handbook',53,'原文将量化位数、准确度与信噪比分别说明',[71,99,522,168]))
card('05','10 m 波段：中心波长、带宽与参考信噪比',
 reg('s2-handbook',53,'表 3：B2、B3、B4、B8 的任务设计指标',[80,180,525,402],[[154,214,334,397],[448,215,524,397]]))
card('06','20 m 波段：红边、窄近红外与短波红外',
 reg('s2-handbook',53,'表 4：历史记号 8b；本文以现行 B8A 对应说明',[80,415,525,697],[[154,447,334,692],[82,610,334,635]]))
card('07','60 m 波段与原生采样分组',
 reg('s2-handbook',54,'表 5：B1、B9、B10 的设计波长与带宽',[80,95,528,276],[[154,129,334,269]]),
 reg('s2-psd',49,'产品规范 15.0：10／20／60 m 的分组仍分别为 4／6／3 个波段',[64,146,528,297],[[66,150,119,297],[448,150,523,297]]))
card('08','光谱信息需要读取文件里的实际字段',
 reg('s2-psd',439,'表 101：采样间距、波长范围、中心与响应采样步长',[35,312,523,432],[[36,314,324,432]]),
 reg('modis-temperature',10,'式 (7)：用传感器响应函数对光谱辐亮度加权',[52,184,559,304],[[61,185,180,266]]))
card('09','重采样改变网格，也可能改变数值',
 reg('ccrs-fundamentals',152,'最近邻：选取原图中最近的像元',[79,350.5,535,424]),
 reg('ccrs-fundamentals',152,'双线性：由四个邻近像元加权',[289,435,530,581]),
 reg('sen2cor-atbd',11,'算法脚注：连续波段与 SCL 分类采用不同重采样规则',[96,713,514,757]))
cards[-1]['regions'].append(reg('sen2cor-atbd',15,'10 m 产品不等于在 10 m 网格独立反演 AOT 和 WV',[96,135,514,285]))
card('10','DN 与 NoData：先辨认有效信号的编码',
 reg('s2-psd',397,'0 是 NoData；1–65535 是可解码信号的编码范围',[55,492,541,519]),
 reg('s2-psd',397,'偏移量用于避免截断负值',[55,518,541,546]))
card('11','辐亮度、辐照度与光谱密度的原始定义',
 reg('nist-radiometry',13,'PDF 第 13 页／书内第 3 页：辐亮度与投影面积、立体角',[40,457,526,534]),
 reg('nist-radiometry',16,'PDF 第 16 页／书内第 6 页：单位面积的辐照度',[192,210,531,280]),
 reg('nist-radiometry',17,'PDF 第 17 页／书内第 7 页：对波长求导的光谱密度',[178,149,531,214]))
card('12','立体角：方向上的面积，而不是地面像元面积',
 reg('ocean-protocols',21,'PDF 第 21 页／书内第 15 页：原图 2.3，单位球面的微分面积',[115,64,478,320]))
card('13','BRDF、反射因子与朗伯模型有不同定义',
 reg('nist-brdf',19,'PDF 第 19 页／书内第 5 页：式 (9)，BRDF 的 sr⁻¹ 单位',[45,620,488,655]),
 reg('nist-brdf',25,'PDF 第 25 页／书内第 11 页：表 1，方向—半球反射率',[59,68,376,91]),
 reg('nist-brdf',26,'PDF 第 26 页／书内第 12 页：表 2，双向反射因子',[29,89,325,111]),
 reg('nist-brdf',57,'PDF 第 57 页／书内第 43 页：式 (C4)，朗伯表面的关系',[157,632,476,656]))
card('14','太阳天顶角、高度角与日地距离字段',
 reg('sen2cor-atbd',67,'式 (0.20)：TOA 反射率与传感器辐亮度的直接关系',[190,105,514,146]),
 reg('landsat-handbook',63,'PDF 第 63 页／书内第 55 页：天顶角与高度角的定义和互余关系',[101,112,535,175]),
 reg('s2-psd',439,'表 101：U 日地距离修正、各波段太阳辐照度',[35,260,729,313]))
card('15','吸收、散射与大气窗口',
 hit('ccrs-fundamentals',12,'散射：粒子或气体改变辐射传播方向',r'Scattering occurs[\s\S]*?original path'),
 hit('ccrs-fundamentals',14,'吸收：大气分子吸收不同波长的能量',r'Absorption is[\s\S]*?various wavelengths'),
 hit('ccrs-fundamentals',14,'大气窗口：受吸收较小的光谱区域',r'Those areas[\s\S]*?windows'))
card('16','路径辐射、透过率与地表项进入同一个模型',
 reg('modis-atmosphere',21,'式 (1)：TOA 辐亮度 = 大气路径项 + 经透射与多次反射的地表项',[70,198,537,245]),
 reg('modis-atmosphere',21,'式 (3)：总透过率中的直射和漫射项',[70,565,536,593]))
card('17','邻近效应：来自相邻地物的大气散射贡献',
 reg('modis-atmosphere',23,'原文将相邻地物、观测辐亮度与大气散射联系起来',[70,570,543,625],[[70,589,543,625]]))
card('18','光学厚度：垂直积分及各组分相加',
 reg('ocean-protocols',32,'式 (2.56)：有限垂直路径；式 (2.57)：完整大气柱',[72,539,507,637],[[234,554,505,582],[234,613,505,637]]),
 reg('ocean-protocols',32,'式 (2.58)：总光学厚度含分子、臭氧、气溶胶贡献',[214,666,508,687]))
card('19','水汽柱含量的单位需要分清',
 reg('s2-l2a',39,'附录 A：L2A 水汽产品的换算与 g·cm⁻² 单位',[64,520,383,546]),
 reg('envi-flaash',21,'表 2-1：atm-cm 与 g/cm² 的数值明显不同',[130,74,533,165],[[282,76,440,165]]))
card('20','产品级别、DEM 正射与地理网格',
 reg('s2-psd',54,'L1B、L1C、L2A 的原始定义；L1C 明确使用 DEM',[108,112,537,191],[[108,138,526,166]]),
 hit('s2-handbook',45,'L1C 输出网格：UTM／WGS84',r'UTM/WGS84'),
 hit('s2-handbook',45,'输出 GSD：10、20、60 m',r'constant Ground Sampling Distance[\s\S]*?different spectral bands'))
card('21','SCL 的每个整数都对应一个类别',
 reg('s2-psd',291,'表 68：0–11 的分类定义；0／1／8–11 是筛选时常查的编码',[108,145,421,450],[[118,199,417,236],[119,365,417,444]]))
card('22','地表反射率、AOT 和 WVP 的换算各不相同',
 reg('s2-l2a',39,'附录 A：两种历史 SR 编码规则；实际数据仍应按元数据解码',[64,201,383,372]),
 reg('s2-l2a',39,'AOT = DN / 1000，无量纲',[64,373,383,400]),
 reg('s2-l2a',39,'WVP = DN / 1000，g·cm⁻²',[64,520,383,546]))
card('23','Landsat 的 Level-1 辐亮度与 Collection 2 L2 编码',
 reg('landsat-handbook',62,'PDF 第 62 页／书内第 54 页：Lλ = ML × Qcal + AL',[101,192,451,335]),
 reg('landsat-c2',18,'PDF 第 18 页／书内第 12 页：表 6-1 的 SR 比例与偏移',[118,84,688,185],[[563,84,688,185]]))
card('24','NDVI 定义与大气的加性、乘性影响',
 reg('modis-vi',28,'PDF 第 28 页／书内第 19 页：正确的差／和形式，式 (5)',[247,661,544,707]),
 reg('modis-vi',40,'PDF 第 40 页／书内第 31 页：路径辐射加性项与透过率乘性项',[70,186,543,215]))
card('25','FLAASH 的模型原式：邻近地表与球面反照率',
 reg('envi-flaash',10,'式 (1)：ρ 与周围地表的平均反射率 ρe 分开进入模型',[212,174,461,215]))
card('26','大气模型是带有温度、水汽与季节条件的假设',
 reg('envi-flaash',21,'表 2-1：三种夏季／热带模型的标准水汽与温度',[130,74,533,165]),
 reg('envi-flaash',21,'表 2-2：纬度与季节选择表；不是只看一个地区名称',[135,212,529,574]))
card('27','水汽反演：FLAASH 的要求与 Sen2Cor 的算法不同',
 reg('envi-flaash',22,'经典 FLAASH：15 nm 或更细，并覆盖吸收特征区间',[128,351,395,369]),
 reg('envi-flaash',22,'原列出的三个覆盖区间',[136,371,369,428]),
 reg('sen2cor-atbd',64,'§4.4：Sen2Cor 使用 B8a 参考波段与 B9 吸收波段',[96,408,514,456]))
card('28','文件格式：GeoTIFF／COG 的结构与存储顺序',
 hit('ogc-cog',17,'BIP：一个像元的各分量连续存储',r'The data is stored as RGBRGBRGB[\s\S]*?BIP\)'),
 hit('ogc-cog',17,'分波段存储：独立分量平面',r'The components are stored in separate component planes'),
 hit('ogc-cog',25,'HTTP Range：请求一个资源的一部分',r'HTTP Version 1.1[\s\S]*?fragment of a resource'))
card('29','真彩色、假彩色与显示拉伸',
 hit('ccrs-fundamentals',21,'多波段被分配给显示屏的 RGB 通道',r'combine and display[\s\S]*?primary colours'),
 hit('ccrs-fundamentals',155,'线性拉伸：扩大范围，提高显示对比度',r'A linear stretch[\s\S]*?contrast in the image'))
card('30','离水辐亮度与水色遥感反射率',
 reg('ocean-protocols',32,'PDF 第 32 页／书内第 26 页：式 (2.54)，RRS = LW / Ed',[226,68,510,105]),
 reg('ocean-protocols',21,'PDF 第 21 页：图 2.4，水面处的反射与折射几何',[100,366,504,582]))
card('31','热红外反演包含地表发射、大气热辐射与发射率',
 reg('modis-temperature',10,'PDF 第 10 页／书内第 8 页：式 (8)，地表与大气的不同热辐射项',[61,441,561,505],[[66,442,280,465]]),
 reg('modis-temperature',10,'原文定义 ε 为地表光谱发射率，B 为同温度黑体辐亮度',[50,510,559,544]))
card('33','辐亮度输入单位与除法缩放',
 reg('envi-flaash',12,'原手册的单位和 scale factor 关系式',[127,599,541,636]))
card('34','经典 FLAASH 参数的原始界面',
 reg('envi-flaash',17,'图 2-1：实际参数字段；旧界面中的设置不是本文推荐默认值',[130,326,531,597],[[275,447,360,499],[361,472,439,499],[292,512,377,558]]),
 hit('envi-flaash',20,'成像时间字段明确使用 GMT',r'Flight Time GMT \(HH:MM:SS\)'))
card('35','QUAC 的输入波段条件也有明确限制',
 hit('envi-flaash',12,'原文要求至少三个波段和有效波长',r'QUAC input files must have[\s\S]*?wavelengths'))
card('36','配准、正射与坡面照明校正是不同步骤',
 hit('ccrs-fundamentals',151,'几何校正：补偿成像过程中的位置畸变',r'Geometric corrections are intended[\s\S]*?real\s+world'),
 hit('ccrs-fundamentals',151,'配准也可以把一幅影像对到另一幅影像',r'Geometric registration may also[\s\S]*?another\s+image'),
 reg('sen2cor-atbd',68,'§4.7：正射需要高程；坡面照明校正还需要坡度、坡向',[96,353,514,438]))
card('37','SAFE 文件组织与 MGRS 瓦片都有正式定义',
 reg('s2-psd',398,'图 4-17：原生 L1C 产品结构图',[118,318,528,431]),
 reg('s2-psd',50,'§2.7.2：UTM／WGS84、MGRS 与 100 km 网格方块',[54,513,542,553]),
 reg('s2-psd',50,'MGRS 是基于 UTM／UPS 的另一套标记方式',[54,639,542,668]))
card('38','Sen2Cor 的查找表与透过率定义',
 reg('sen2cor-atbd',51,'式 (0.1)：路径辐射、透过率、地表辐照度与反射率',[130,517,514,553]),
 hit('sen2cor-atbd',51,'LUT：预先计算不同几何、高程和大气参数的传播关系',r'LibRadtran[\s\S]*?atmospheric parameters'))
card('39','波数单位与 FWHM 这个名字的完整含义',
 reg('nist-radiometry',12,'§1.1.1：波数是单位长度中的波数，单位为长度的倒数',[40,626,516,686]),
 hit('envi-flaash',12,'FWHM = full width half maximum',r'full width half maximum[\s\S]*?\(FWHM\)'))

def render(c):
 pieces=[]
 for r in c['regions']:
  name=r['source'];n=r['pdf_page'];box=r['box']
  assert 0 <= box[0] < box[2] <= page(name,n).width
  assert 0 <= box[1] < box[3] <= page(name,n).height
  if name not in pdfs: pdfs[name]=pdfium.PdfDocument(ROOT/'cache'/(name+'.pdf'))
  original=pdfs[name][n-1].render(scale=SCALE).to_pil().convert('RGB')
  crop=original.crop(tuple(round(v*SCALE) for v in box))
  draw=ImageDraw.Draw(crop)
  # Red outer frame marks the entire quoted excerpt; inner frames mark table columns/cells.
  draw.rectangle((1,1,crop.width-2,crop.height-2),outline='#cf202f',width=3)
  for h in r['highlights']:
   coords=[round((h[0]-box[0])*SCALE),round((h[1]-box[1])*SCALE),round((h[2]-box[0])*SCALE),round((h[3]-box[1])*SCALE)]
   draw.rectangle(coords,outline='#cf202f',width=3)
  factor=min(1,(WIDTH-112)/crop.width)
  if factor<1: crop=crop.resize((round(crop.width*factor),round(crop.height*factor)),Image.Resampling.LANCZOS)
  pieces.append((r,crop))
 height=132+sum(96+im.height for _,im in pieces)+28
 canvas=Image.new('RGB',(WIDTH,height),'#f6f7fa');d=ImageDraw.Draw(canvas)
 def text(x,y,t,size=23,color='#253248'): d.text((x,y),t,font=ImageFont.truetype(FONT,size),fill=color)
 text(45,25,f'原文证据 {c["id"]} · {c["title"]}',29)
 text(45,76,'原 PDF 直接渲染；中文为本文说明，红框为本文标注，未重排原文。',22,'#697386')
 y=128
 for r,im in pieces:
  text(45,y,r['label'],23);y+=35
  text(45,y,f'{TITLES[r["source"]]} · PDF 第 {r["pdf_page"]} 页',19,'#697386');y+=34
  canvas.paste(im,(56,y));y+=im.height+27
 canvas.save(OUT/c['file'],optimize=True)
 c['sha256']=hashlib.sha256((OUT/c['file']).read_bytes()).hexdigest()
 c['width']=WIDTH;c['height']=height
 for r in c['regions']:
  r['source_url']=manuals[r['source']]['url']
  r['source_sha256']=hashlib.sha256((ROOT/'cache'/(r['source']+'.pdf')).read_bytes()).hexdigest()
  r['extracted_text']=page(r['source'],r['pdf_page']).crop(r['box']).extract_text() or ''
 print(c['id'],c['file'],height)

if __name__=='__main__':
 assert not any('MISSING' in r['highlights'] for c in cards for r in c['regions']), 'Resolve every missing source phrase before rendering'
 for c in cards: render(c)
 (ROOT/'evidence-figures.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # A review sheet is a preview only, never an article image.
 thumbs=[]
 for c in cards:
  im=Image.open(OUT/c['file']);im.thumbnail((330,580))
  panel=Image.new('RGB',(350,620),'white');panel.paste(im,((350-im.width)//2,20));
  ImageDraw.Draw(panel).text((12,598),c['id'],font=ImageFont.truetype(FONT,17),fill='black')
  thumbs.append(panel)
 sheet=Image.new('RGB',(350*5,620*((len(thumbs)+4)//5)),'#d4d8df')
 for i,im in enumerate(thumbs):sheet.paste(im,((i%5)*350,(i//5)*620))
 sheet.save(ROOT/'cache/evidence-contact-sheet.jpg')
