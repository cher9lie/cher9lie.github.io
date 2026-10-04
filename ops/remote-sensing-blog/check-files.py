"""Check the published links without storing large imagery in the blog repository."""
import pathlib,json,urllib.request,urllib.error,concurrent.futures,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'src/content/blog/flaash-atmospheric-correction-concepts'
j=json.loads((ROOT/'cog-0.json').read_text())
def check(k):
    url=j['assets'][k]['href']
    req=urllib.request.Request(url,headers={'Range':'bytes=0-8191'})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            status=r.status;headers=dict(r.headers);data=r.read(8192)
        return {'asset':k,'url':url,'http_status':status,'content_type':headers.get('Content-Type'),'content_range':headers.get('Content-Range'),'sample_bytes':len(data),'first_bytes_hex':data[:4].hex()}
    except Exception as e:return {'asset':k,'url':url,'error':str(e)}
keys=['blue','green','red','nir','nir09','swir16','swir22','scl','aot','wvp','visual']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:report=list(ex.map(check,keys))
for k in ['thumbnail','granule_metadata','tileinfo_metadata']:
    u=j['assets'][k]['href']
    with urllib.request.urlopen(u,timeout=40) as r:
        data=r.read();status=r.status
    name={'thumbnail':'sentinel-real-thumbnail.jpg','granule_metadata':'example-granule-metadata.xml','tileinfo_metadata':'example-tileinfo.json'}[k]
    (OUT/name if k=='thumbnail' else ROOT/name).write_bytes(data)
    report.append({'asset':k,'url':u,'http_status':status,'downloaded_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(ROOT/'download-checks.json').write_text(json.dumps({'checked_on':'2026-10-05','item':j['id'],'checks':report},indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
