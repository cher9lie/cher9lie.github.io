from pathlib import Path
import json, urllib.parse
ROOT=Path(__file__).resolve().parent
article=ROOT.parents[1]/'src/content/blog/flaash-atmospheric-correction-concepts/index.md'
def link(s):return urllib.parse.quote(s,safe=':/?=$,@#&')
j=json.loads((ROOT/'files-L1C.json').read_text())
wanted=[('MTD_MSIL1C.xml','产品级元数据：量化、偏移、辐照度等'),('MTD_TL.xml','瓦片级元数据：采集时间、投影、角度等'),('T33TVM_20200915T101031_B04.jp2','红光，10 m'),('T33TVM_20200915T101031_B08.jp2','近红外，10 m'),('T33TVM_20200915T101031_B09.jp2','水汽波段，60 m')]
rows=['| 文件 | 内容 | 记录大小 | 实际文件页与下载 |','| --- | --- | --- | --- |']
for name,desc in wanted:
 x=next(x for x in j['files'] if x['name']==name)
 rows.append(f"| `{name}` | {desc} | {x['bytes']:,} 字节 | [文件页]({link(x['nodes'])}) · [下载]({link(x['download'])}) |")
native='\n'.join(rows)
j=json.loads((ROOT/'cog-0.json').read_text())
checks=json.loads((ROOT/'download-checks.json').read_text())['checks']
rows=['| 文件 | 内容／资产网格 | 实際下载地址 |','| --- | --- | --- |']
names={'blue':'蓝光','green':'绿光','red':'红光','nir':'近红外','nir09':'水汽波段','swir16':'短波红外','swir22':'短波红外','scl':'场景分类','aot':'气溶胶光学厚度','wvp':'水汽柱含量','visual':'真彩色显示','granule_metadata':'瓦片 XML 元数据','tileinfo_metadata':'瓦片 JSON 信息'}
for k,desc in names.items():
 a=j['assets'][k];name=a['href'].rsplit('/',1)[1]
 if 'gsd' in a:desc+=f"，{a['gsd']} m"
 rows.append(f"| `{name}` | {desc} | [下载 {name}]({a['href']}) |")
public='\n'.join(rows).replace('実際','实际')
t=article.read_text(encoding='utf-8')
assert '<!-- NATIVE_FILES -->' in t and '<!-- PUBLIC_FILES -->' in t
article.write_text(t.replace('<!-- NATIVE_FILES -->',native).replace('<!-- PUBLIC_FILES -->',public),encoding='utf-8')
print('inserted',len(wanted),'native file links and',len(names),'public assets')
