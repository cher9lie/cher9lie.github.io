"""Print original PDF line locations to select reproducible crop rectangles."""
from pathlib import Path
import sys
import pdfplumber
root=Path(__file__).resolve().parent/'cache'
with pdfplumber.open(root/(sys.argv[1]+'.pdf')) as doc:
 for n in sys.argv[2:]:
  p=doc.pages[int(n)-1]
  print('PAGE',n,'SIZE',p.width,p.height)
  for line in p.extract_text_lines():
   print(round(line['x0'],1),round(line['top'],1),round(line['x1'],1),round(line['bottom'],1),line['text'])
