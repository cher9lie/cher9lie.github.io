"""Retrieve primary references and a real Sentinel-2 pair; no login needed."""
import json, urllib.request, urllib.parse, pathlib, concurrent.futures, hashlib
ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / 'cache'
CACHE.mkdir(exist_ok=True)
PDFS = {
 'envi-flaash': 'https://www.nv5geospatialsoftware.com/portals/0/pdfs/envi/QUAC_FLAASH_Module.pdf',
 's2-psd': 'https://sentinels.copernicus.eu/documents/d/sentinel/s2-pdgs-cs-di-psd-v15-0',
 's2-l2a': 'https://step.esa.int/thirdparties/sen2cor/2.10.0/docs/S2-PDGS-MPC-L2A-PDD-V14.9-v4.9.pdf',
}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RemoteSensingReferenceCheck/1.0'}),timeout=60) as r:
        return r.read(), r.status, r.geturl()
def pdf(item):
    name,url = item
    p=CACHE/(name+'.pdf')
    if not p.exists(): p.write_bytes(get(url)[0])
    return {'name':name,'url':url,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    manifest=list(pool.map(pdf,PDFS.items()))
(ROOT/'manuals.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('manuals',[(x['name'],x['bytes']) for x in manifest])
for level in ['L1C','L2A']:
    query="contains(Name,'S2A_MSI%s_20200915T101031') and contains(Name,'T33TVM')"%level
    url='https://catalogue.dataspace.copernicus.eu/odata/v1/Products?'+urllib.parse.urlencode({'$filter':query,'$expand':'Attributes','$top':10})
    raw,status,_=get(url)
    (CACHE/('catalog-'+level+'.json')).write_bytes(raw)
    data=json.loads(raw)
    print(level,status,[(x['Id'],x['Name']) for x in data.get('value',[])])
url='https://earth-search.aws.element84.com/v1/search?'+urllib.parse.urlencode({'collections':'sentinel-2-l2a','datetime':'2020-09-15T00:00:00Z/2020-09-15T23:59:59Z','bbox':'13,46,13.5,46.5','limit':10})
try:
    raw,status,_=get(url);(CACHE/'earthsearch.json').write_bytes(raw)
    print('earthsearch',status,[(x['id'],x['properties'].get('s2:product_uri')) for x in json.loads(raw).get('features',[])])
except Exception as e: print('earthsearch',type(e).__name__,str(e))
