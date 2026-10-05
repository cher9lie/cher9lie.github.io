"""Render full original manual pages and mark their relevant areas."""
from pathlib import Path
import hashlib,json
import pypdfium2 as pdfium
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'src/content/blog/flaash-atmospheric-correction-concepts'
SCALE=3

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def render_pages():
    cards=json.loads((HERE/'evidence-figures.json').read_text(encoding='utf-8'))
    old=json.loads((HERE/'figure-sources.json').read_text(encoding='utf-8'))
    sources={m['name']:m for m in json.loads((HERE/'evidence-manuals.json').read_text(encoding='utf-8'))}
    pages={}
    for card in cards:
        for r in card['regions']:
            key=(r['source'],r['pdf_page'])
            target=pages.setdefault(key,{'regions':[],'notes':[]})
            target['regions'].extend(r['highlights'] or [r['box']])
            target['notes'].append(r['label'])
    for card in old:
        key=(card['source'],card['pdf_page'])
        target=pages.setdefault(key,{'regions':[],'notes':[]})
        for label,box in card['regions']:
            target['regions'].append(box);target['notes'].append(label)
    result=[]
    for (name,num),data in pages.items():
        path=HERE/'cache'/(name+'.pdf')
        doc=pdfium.PdfDocument(path)
        page=doc[num-1]
        size=page.get_size()
        im=page.render(scale=SCALE).to_pil().convert('RGB')
        draw=ImageDraw.Draw(im)
        unique=[]
        for box in data['regions']:
            if any(all(abs(a-b)<1 for a,b in zip(box,other)) for other in unique):continue
            unique.append(box)
            assert 0<=box[0]<box[2]<=size[0] and 0<=box[1]<box[3]<=size[1],(name,num,box,size)
            # The full page, margins, headers and page number remain visible.
            draw.rectangle(tuple(round(v*SCALE) for v in box),outline='#d92332',width=4)
        file=f'manual-{name}-p{num:03}.png'
        im.save(OUT/file,optimize=True)
        result.append({'source':name,'pdf_page':num,'file':file,'source_url':sources[name]['url'],
                       'source_sha256':sha(path),'sha256':sha(OUT/file),'page_size_points':size,
                       'width':im.width,'height':im.height,'scale':SCALE,'regions':unique,'notes':data['notes']})
        print(name,num,im.size)
        doc.close()
    # XLSX contains figures rather than paginated PDF pages. Keep each entire
    # original embedded diagram as its own illustration.
    for source,file,box in [
        ('srf-Equivalent-Wavelengths-0.png','manual-srf-equivalent.png',(80,44,330,143)),
        ('srf-Bandwidth-and-mid-wavelength-0.png','manual-srf-bandwidth.png',(67,353,419,411))]:
        im=Image.open(HERE/'cache'/source).convert('RGB')
        ImageDraw.Draw(im).rectangle(box,outline='#d92332',width=2)
        im=im.resize((im.width*3,im.height*3),Image.Resampling.LANCZOS)
        im.save(OUT/file,optimize=True)
    (HERE/'manual-pages.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':render_pages()
