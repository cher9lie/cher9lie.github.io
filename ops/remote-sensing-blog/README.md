# 遥感文章的原始文件摘图

`evidence-research.py` 下载 15 份原始 PDF，检查 PDF 文件头、记录页数与 SHA-256，并生成逐页文本索引。`evidence-figures.py` 用 PDFium 渲染原页，按 PDF 点坐标裁切后标红框；不重新排版原文。`evidence-srf.py` 提取官方 XLSX 的原始内嵌图，并核对 S2A 波长列的 1 nm 步长；不保存、修改原 XLSX。

环境需要 Python，以及 `pypdf`、`pdfplumber`、`pypdfium2`、`Pillow`、`openpyxl`。中文标题使用 Windows 的微软雅黑字体，其他系统可改脚本中的字体路径。

在仓库根目录依次执行：

```text
python ops/remote-sensing-blog/evidence-research.py
python ops/remote-sensing-blog/evidence-figures.py
python ops/remote-sensing-blog/evidence-srf.py
npm run build
python ops/remote-sensing-blog/evidence-check.py
```

原文件存于忽略的 `cache/`；摘图、来源和坐标记录分别存于文章目录及 `evidence-figures.json`。32 号为 XLSX 原图，其余 38 组为 PDF 摘图。PDF 页码从 1 开始，指浏览器页序；书内页码在图注另列。

`evidence-checks.json` 是实际文件、来源页码链接、图片哈希、波段表和构建产物的检查结果。`evidence-editorial-review.json` 记录三轮自查及修订，不代表独立同行评审，也不代表完成真实影像的大气校正精度实验。`evidence-find.py` 与 `evidence-lines.py` 用于查找原文和定位裁切坐标。
