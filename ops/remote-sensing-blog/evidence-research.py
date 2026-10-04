"""Download primary technical PDFs and index their pages for excerpt selection."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'cache'
SOURCES = {
 'ogc-cog': 'https://docs.ogc.org/is/21-026/21-026.pdf',
 'sen2cor-atbd': 'https://sentiwiki.copernicus.eu/__attachments/a_2e88ffb8dabc4e1ec9efb71ba27cc9bcf70feeb378c084a2e80ba990273ebe5c/S2-PDGS-MPC-ATBD-L2A%20-%20Level%202A%20Algorithm%20Theoretical%20Basis%20Document%202021%20-%202.10.pdf',
 'landsat-c2': 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat8-9-Collection2-Level2-Science-Product-Guide-v6.pdf',
 's2-handbook': 'https://sentinels.copernicus.eu/documents/247904/685211/Sentinel-2_User_Handbook',
 'nist-radiometry': 'https://nvlpubs.nist.gov/nistpubs/Legacy/hb/nisthandbook152.pdf',
 'nist-brdf': 'https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nbsmonograph160.pdf',
 'ccrs-fundamentals': 'https://natural-resources.canada.ca/sites/nrcan/files/earthsciences/pdf/resource/tutor/fundam/pdf/fundamentals_e.pdf',
 'landsat-handbook': 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/LSDS-1574_L8_Data_Users_Handbook-v5.0.pdf',
 'modis-vi': 'https://modis.gsfc.nasa.gov/data/atbd/atbd_mod13.pdf',
 'modis-atmosphere': 'https://modis.gsfc.nasa.gov/data/atbd/atbd_mod08.pdf',
 'modis-temperature': 'https://modis.gsfc.nasa.gov/data/atbd/atbd_mod11.pdf',
 'ocean-protocols': 'https://oceancolor.gsfc.nasa.gov/files/resources/docs/technical/protocols_ver4_voli.pdf',
 's2-psd': 'https://sentinels.copernicus.eu/documents/d/sentinel/s2-pdgs-cs-di-psd-v15-0',
 's2-l2a': 'https://step.esa.int/thirdparties/sen2cor/2.10.0/docs/S2-PDGS-MPC-L2A-PDD-V14.9-v4.9.pdf',
 'envi-flaash': 'https://www.nv5geospatialsoftware.com/portals/0/pdfs/envi/QUAC_FLAASH_Module.pdf',
}

def get_pdf(item):
 name,url=item
 path=CACHE/(name+'.pdf')
 if not path.exists():
  req=urllib.request.Request(url,headers={'User-Agent':'RemoteSensingReferenceCheck/1.0'})
  with urllib.request.urlopen(req,timeout=55) as r:
   data=r.read()
   assert data.startswith(b'%PDF'),(url,r.geturl())
   path.write_bytes(data)
 reader=PdfReader(path)
 pages=[p.extract_text() or '' for p in reader.pages]
 (CACHE/(name+'-pages.json')).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
 return {'name':name,'url':url,'pages':len(pages),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':
 CACHE.mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=4) as pool:
  manifest=list(pool.map(get_pdf,SOURCES.items()))
 (ROOT/'evidence-manuals.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(manifest,ensure_ascii=False,indent=2))
