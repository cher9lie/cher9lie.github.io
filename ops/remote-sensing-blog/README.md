# 遥感文章的手册页面与来源记录

`evidence-research.py` 下载 15 份原始 PDF，检查文件头，记录页数、SHA-256，并生成逐页文本索引。`evidence-srf.py` 提取官方 XLSX 的内嵌图，核对 S2A 波长列的 1 nm 步长。

当前文章使用 `manual-pages.py` 生成完整手册页面：按原尺寸渲染 PDF，只在对应区域添加红框，保留原页的正文、页眉、页脚和页码。相同来源的同一页合并为一张图。XLSX 的两个内嵌图分别保留完整原图。

环境需要 Python，以及 `pypdf`、`pdfplumber`、`pypdfium2`、`Pillow`、`openpyxl`。

在仓库根目录依次执行：

```text
python ops/remote-sensing-blog/evidence-research.py
python ops/remote-sensing-blog/evidence-srf.py
python ops/remote-sensing-blog/manual-pages.py
npm run build
python ops/remote-sensing-blog/presentation-check.py
```

原文件存于忽略的 `cache/`；59 张完整 PDF 页面和 2 张 XLSX 原图存于文章目录。`manual-pages.json` 记录原文件、源页、尺寸、图像哈希与红框坐标；`presentation-figures.json` 记录正文的图号、图名及引用锚点。PDF 页码按浏览器从 1 开始计数，书内页码在图注另列。

`presentation-checks.json` 保存实际检查结果，包括完整页面尺寸、红框以外的像素与原页一致、图注、公式及跳转链接。`presentation-editorial-review.json` 记录本轮三次自查。浏览器另行检查加粗显示、折叠页展开和图号跳转。

此前的 `evidence-figures.py`、图版及相关检查记录保留为制作历史；其中的 PDF 坐标供完整页面渲染器复用。`evidence-find.py` 与 `evidence-lines.py` 用于定位原文。
