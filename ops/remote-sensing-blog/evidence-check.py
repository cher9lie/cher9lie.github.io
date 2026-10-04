"""Audit source provenance, excerpt assets, anchors and the built article."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re
from PIL import Image
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTICLE = ROOT / 'src/content/blog/flaash-atmospheric-correction-concepts'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.images = []
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'img':
            self.images.append(attrs)
        if tag == 'a':
            self.hrefs.append(attrs.get('href', ''))

if __name__ == '__main__':
    md = (ARTICLE / 'index.md').read_text(encoding='utf-8')
    built = ROOT / 'dist/blog/flaash-atmospheric-correction-concepts/index.html'
    rendered = built.read_text(encoding='utf-8')
    page = Page()
    page.feed(rendered)
    figures = json.loads((HERE/'evidence-figures.json').read_text(encoding='utf-8'))
    manuals = json.loads((HERE/'evidence-manuals.json').read_text(encoding='utf-8'))
    srf = json.loads((HERE/'evidence-srf.json').read_text(encoding='utf-8'))
    assert len(figures) == 38
    assert {f['id'] for f in figures} | {'32'} == {f'{i:02}' for i in range(1,40)}
    for m in manuals:
        path = HERE/'cache'/(m['name']+'.pdf')
        assert path.read_bytes().startswith(b'%PDF')
        assert sha(path) == m['sha256']
        assert len(PdfReader(path).pages) == m['pages']
    sources = set()
    regions = 0
    for f in figures:
        path = ARTICLE/f['file']
        assert sha(path) == f['sha256'], path
        with Image.open(path) as im:
            assert im.size == (f['width'], f['height'])
        assert f'(./{f["file"]})' in md
        assert f'evidence-{f["id"]}' in page.ids
        for r in f['regions']:
            source = HERE/'cache'/(r['source']+'.pdf')
            assert sha(source) == r['source_sha256']
            # Original raster diagrams, the embedded scale equation, and GUI
            # screenshot have no PDF text layer; they were visually checked.
            raster_regions = {('12','ocean-protocols',21),('30','ocean-protocols',21),
                              ('33','envi-flaash',12),('34','envi-flaash',17),
                              ('37','s2-psd',398)}
            assert r['extracted_text'].strip() or (f['id'],r['source'],r['pdf_page']) in raster_regions, r
            assert r['source_url'] + '#page=' + str(r['pdf_page']) in md, r
            sources.add(r['source'])
            regions += 1
    assert sha(HERE/'cache/s2-srf-v4.xlsx') == srf['file_sha256']
    assert srf['wavelength_step_nm'] == 1
    assert srf['wavelength_extent_nm'] == [300,2600]
    assert srf['source_url'] in md
    assert 'evidence-32' in page.ids
    assert (ARTICLE/srf['rendered_file']).exists()
    expected = len(re.findall(r'^\$\$$', md, re.M)) // 2
    equations = len(re.findall(r'class="katex-display"', rendered))
    assert equations == expected == 22, (equations,expected)
    assert 'katex-error' not in rendered
    assert not re.search(r'\\\\(?:lambda|frac|int|mathrm)',md)
    evidence_images = [im for im in page.images if '原文证据' in im.get('alt','')]
    assert len(evidence_images) == 39, len(evidence_images)
    for im in evidence_images:
        assert im.get('width') and im.get('height')
        target = ROOT/'dist'/im['src'].lstrip('/')
        assert target.exists(), target
        with Image.open(target) as image:
            assert image.format == 'WEBP'
    for href in page.hrefs:
        if href.startswith('#evidence-'):
            assert href[1:] in page.ids, href
    bands = re.findall(r'^\| (B\d+A?) \| (\d+) nm \| (\d+) nm \| (\d+) m \|',md,re.M)
    assert len(bands) == 13
    assert [int(row[2]) for row in bands] == [20,65,35,30,15,15,20,115,20,20,30,90,180]
    assert {gsd:sum(row[3] == gsd for row in bands) for gsd in ['10','20','60']} == {'10':4,'20':6,'60':3}
    for text in ['最陡斜率','A2:A2302','没有在 10 m 空间尺度进行 AOT 和 WV 反演','12 位','16 位','Input Scale','PB 02.14','PB 05.00']:
        assert text in md, text
    report = {
        'date':'2026-10-05',
        'status':'passed',
        'source_method':'Downloaded original files verified by PDF signature, page count and SHA-256; no generated replacement of source text.',
        'new_original_document_figures':39,
        'new_pdf_excerpt_regions':regions,
        'visually_checked_raster_regions_without_text_layer':5,
        'referenced_pdf_sources':len(sources),
        'cached_downloaded_pdfs_verified':len(manuals),
        'srf_original_xlsx_sha256':srf['file_sha256'],
        'srf_figure_sha256':sha(ARTICLE/srf['rendered_file']),
        'source_page_links_and_figure_anchors':'passed',
        'native_band_counts':{'10m':4,'20m':6,'60m':3},
        'display_equations':equations,
        'katex_errors':0,
        'optimized_evidence_images':len(evidence_images),
        'all_optimized_images_present':'passed',
    }
    (HERE/'evidence-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
