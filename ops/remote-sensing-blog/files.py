import json, urllib.request, pathlib, concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=ROOT/'cache'
def get(url):
 with urllib.request.urlopen(url,timeout=45) as r:return r.read()
def walk(level):
 product=json.loads((CACHE/('catalog-'+level+'.json')).read_text())['value'][0]
 base='https://download.dataspace.copernicus.eu/odata/v1/Products('+product['Id']+')'
 out=[]
 def nodes(url,depth=0):
  try:data=json.loads(get(url))
  except Exception as e:print('nodes-error',level,str(e));return
  for n in data.get('result',[]):
   name=n['Name'];uri=n.get('Nodes',{}).get('uri')
   if n.get('ChildrenNumber',0)>0 and uri:
    if depth<6 and (depth<2 or name in ['GRANULE','IMG_DATA','R10m','R20m','R60m'] or name.startswith('L')): nodes(uri,depth+1)
   else:
    endpoint=url.rstrip('/Nodes') if False else url.removesuffix('/Nodes')+'/Nodes('+name+')/$value'
    out.append({'name':name,'bytes':n.get('ContentLength'),'download':endpoint,'nodes':url})
 nodes(base+'/Nodes')
 product['files']=out
 (ROOT/('files-'+level+'.json')).write_text(json.dumps(product,indent=2),encoding='utf-8')
 print(level,product['Name'],'files',len(out))
 for x in out:
  if any(k in x['name'] for k in ['MTD_','B04','B08','B09']):print(x['name'],x['bytes'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(walk,['L1C','L2A']))
for index in [1,0]:
 u=f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2A_33TVM_20200915_{index}_L2A'
 try:
  data=json.loads(get(u));(ROOT/f'cog-{index}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
  print('COG',data['id'])
  for k in ['red','nir','blue','green','scl','visual','granule_metadata','product_metadata']:
   a=data.get('assets',{}).get(k)
   if a: print(k,a['href'])
 except Exception as e:print('COG',index,str(e))
