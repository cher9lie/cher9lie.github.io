"""Verify complete original pages, annotations and the rendered presentation."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re
import pypdfium2 as pdfium
from PIL import Image,ImageDraw,ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARTICLE=ROOT/'src/content/blog/flaash-atmospheric-correction-concepts'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.images=[];self.links=[];self.captions=0;self.details=0;self.quotes=0;self.underlines=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='img':self.images.append(a)
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='figcaption':self.captions+=1
        if tag=='details':self.details+=1
        if tag=='blockquote':self.quotes+=1
        if tag=='u':self.underlines+=1

if __name__=='__main__':
    pages=json.loads((HERE/'manual-pages.json').read_text(encoding='utf-8'))
    figures=json.loads((HERE/'presentation-figures.json').read_text(encoding='utf-8'))
    md=(ARTICLE/'index.md').read_text(encoding='utf-8')
    html=(ROOT/'dist/blog/flaash-atmospheric-correction-concepts/index.html').read_text(encoding='utf-8')
    assert len(pages)==59 and len(figures)==65
    assert '原文证据' not in md and '不代表' not in md and '不作为' not in md
    assert '，。' not in md and not re.search(r'[。；，]> ',md)
    page=Page();page.feed(html)
    assert page.captions==65,page.captions
    assert page.details>=10 and page.quotes>=3 and page.underlines>=2
    assert len(re.findall(r'class="katex-display"',html))==22 and 'katex-error' not in html
    verified=0
    for p in pages:
        original=HERE/'cache'/(p['source']+'.pdf')
        assert sha(original)==p['source_sha256']
        target=ARTICLE/p['file']
        assert sha(target)==p['sha256']
        assert p['source_url']+'#page='+str(p['pdf_page']) in md
        doc=pdfium.PdfDocument(original)
        raw=doc[p['pdf_page']-1].render(scale=p['scale']).to_pil().convert('RGB')
        with Image.open(target) as marked:
            assert marked.size==raw.size==(p['width'],p['height'])
            mask=Image.new('RGB',raw.size,'white')
            draw=ImageDraw.Draw(mask)
            for box in p['regions']:
                draw.rectangle(tuple(round(v*p['scale']) for v in box),outline='black',width=4)
            diff=ImageChops.difference(raw,marked.convert('RGB'))
            assert ImageChops.multiply(diff,mask).getbbox() is None,p['file']
        doc.close();verified+=1
    active=[]
    for f in figures:
        assert '(./'+f['file']+')' in md
        if 'anchor' in f:assert f['anchor'] in page.ids
        matching=[im for im in page.images if '/'+f['file'].removesuffix('.png').removesuffix('.jpg')+'.' in im.get('src','')]
        assert len(matching)==(2 if f['file']=='atmosphere-path.png' else 1),(f['file'],len(matching))
        im=matching[-1]
        assert im.get('width') and im.get('height')
        asset=ROOT/'dist'/im['src'].lstrip('/')
        assert asset.exists()
        with Image.open(asset) as image:assert image.format=='WEBP'
        active.append(im['src'])
    for link in page.links:
        if link.startswith(('#page-','#evidence-')):assert link[1:] in page.ids,link
    for n in range(1,40):assert f'evidence-{n:02}' in page.ids
    bands=re.findall(r'^\| (B\d+A?) \| (\d+) nm \| (\d+) nm \| (\d+) m \|',md,re.M)
    assert len(bands)==13
    assert [int(b[2]) for b in bands]==[20,65,35,30,15,15,20,115,20,20,30,90,180]
    report={'date':'2026-10-05','status':'passed','full_original_pdf_pages':verified,
            'pixels_outside_red_frames_match_original_render':True,
            'original_xlsx_figures':2,'figures_with_captions':page.captions,
            'supplementary_page_groups':page.details,'blockquote_count':page.quotes,
            'underline_count':page.underlines,'display_equations':22,'katex_errors':0,
            'image_assets':active,'cross_references':'passed'}
    (HERE/'presentation-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='image_assets'},ensure_ascii=False,indent=2))
