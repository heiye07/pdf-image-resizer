# PDF 图片像素压缩

从 [Releases](https://github.com/heiye07/pdf-image-resizer/releases) 下载 Windows 程序 `PDF-Image-Resizer.exe`，双击运行，添加 PDF，选择缩放方式，点击开始压缩。无需安装 Python。

- 最长边：默认 2000，6000×9000 会缩到 1333×2000；也可以自行设为 3000，得到 2000×3000。
- 百分比：宽高分别乘以指定百分比。
- 宽高范围：例如 2000×3000，图片等比例缩小以放入此范围，不拉伸、不裁剪。
- JPEG 质量独立设置，默认 90。未缩小的图片原样保留，不重新编码。
- 支持多文件；结果另存，文件名重复时自动添加编号。
- 图片对象只处理一次，同一图片在多页出现时同步生效。
- 透明图片使用 PNG；含特殊蒙版的图片跳过并记录。内联图片不在处理范围内。
- 保留页面大小及现有文字、矢量、链接等对象，不把整页转换成图片。
- 加密文件和带签名字段的文件需要先准备解密或未签名副本。
- 像素缩小会减少细节；不能承诺每种原始编码都获得更小文件。
- 本机离线处理，应用不上传文件。

## 开发

Python 3.12，依赖见 requirements.txt。

安装依赖：`python -m pip install -r requirements.txt`

运行：`python app.py`

打包：`python -m PyInstaller --noconfirm --clean --onefile --windowed --name PDF图片像素压缩 app.py`

验证：`python -m unittest -v test_core`

当前提供 Windows 版本，暂未适配和验证 macOS。

PyMuPDF 为 AGPL / 商业双重许可；如要分发或商用集成，请遵循依赖许可。此版本提供完整应用源码。
