from pathlib import Path
import json
import sys

root=Path(__file__).resolve().parent/'cache'
name=sys.argv[1]
pages=json.loads((root/(name+'-pages.json')).read_text(encoding='utf-8'))
for selector in sys.argv[2:]:
 if selector.isdigit():
  print('\nPDF PAGE',selector,'\n',pages[int(selector)-1])
 else:
  print('\nTERM',selector)
  for i,p in enumerate(pages):
   k=p.lower().find(selector.lower())
   if k>=0:
    print('PDF PAGE',i+1,repr(p[max(0,k-130):k+300]))
