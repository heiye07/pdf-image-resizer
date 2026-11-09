from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import math
import os
import tempfile
import pymupdf as fitz
from PIL import Image


@dataclass
class Settings:
    mode: str = 'longest'
    longest: int = 2000
    percent: float = 33.333333
    width: int = 2000
    height: int = 3000
    quality: int = 90

    def validate(self):
        if self.mode not in ('longest', 'percent', 'box'):
            raise ValueError('未知缩放模式')
        if not 1 <= self.quality <= 100:
            raise ValueError('JPEG 质量需要在 1～100 之间')
        if self.longest < 1 or self.width < 1 or self.height < 1:
            raise ValueError('像素尺寸必须大于 0')
        if not math.isfinite(self.percent) or not 0 < self.percent <= 100:
            raise ValueError('缩放比例需要大于 0 且不超过 100%')

    def size(self, w, h):
        if self.mode == 'longest':
            ratio = min(1, self.longest / max(w, h))
        elif self.mode == 'percent':
            ratio = self.percent / 100
        else:
            ratio = min(1, self.width / w, self.height / h)
        return max(1, round(w * ratio)), max(1, round(h * ratio))


def compress(source, target, settings, log=lambda _: None, cancelled=lambda: False):
    settings.validate()
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError('输出文件不能覆盖原文件')
    if target.exists():
        raise ValueError('输出文件已存在，请换一个文件名')
    changed = skipped = 0
    temp = None
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError('此 PDF 有密码，请先解密后再处理')
            if doc.get_sigflags() > 0:
                raise ValueError('此 PDF 含签名字段，请使用未签名副本处理')
            refs = {}
            for page in doc:
                for info in page.get_images(full=True):
                    refs.setdefault(info[0], (page.number, info))
            log(f'共 {len(doc)} 页，发现 {len(refs)} 个独立图片对象')
            for index, (xref, (page_no, info)) in enumerate(refs.items(), 1):
                if cancelled():
                    raise InterruptedError('已取消，未保存输出文件')
                w, h = info[2:4]
                nw, nh = settings.size(w, h)
                if (nw, nh) == (w, h):
                    skipped += 1
                    log(f'[{index}/{len(refs)}] {w}×{h}：保留原图')
                    continue
                # Preserve soft alpha; skip color-key and explicit masks rather than
                # silently changing their appearance.
                mask_kind, _ = doc.xref_get_key(xref, 'Mask')
                if mask_kind != 'null':
                    skipped += 1
                    log(f'[{index}/{len(refs)}] {w}×{h}：含特殊蒙版，已跳过')
                    continue
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.colorspace is None:
                        raise ValueError('独立蒙版')
                    if pix.colorspace.n not in (1, 3):
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    if info[1]:
                        pix = fitz.Pixmap(pix, fitz.Pixmap(doc, info[1]))
                    # PNG serialization unpremultiplies MuPDF's alpha samples.
                    image = Image.open(BytesIO(pix.tobytes('png')))
                    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
                    buffer = BytesIO()
                    if pix.alpha:
                        image.save(buffer, format='PNG', optimize=True)
                    else:
                        image.save(buffer, format='JPEG', quality=settings.quality, optimize=True, subsampling=0)
                    doc[page_no].replace_image(xref, stream=buffer.getvalue())
                    changed += 1
                    log(f'[{index}/{len(refs)}] {w}×{h} → {nw}×{nh}' + ('（保留透明度）' if pix.alpha else ''))
                except Exception as exc:
                    # An unexpected replace failure must abort, as it may have
                    # partially modified the document in memory.
                    raise RuntimeError(f'图片 {xref} 处理失败：{exc}') from exc
            if cancelled():
                raise InterruptedError('已取消，未保存输出文件')
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
            os.close(fd)
            doc.save(temp, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        with fitz.open(temp) as check:
            if check.page_count == 0:
                raise RuntimeError('输出校验失败')
        # Windows rename refuses to replace an existing destination.
        os.rename(temp, target)
        temp = None
        before, after = source.stat().st_size, target.stat().st_size
        log(f'完成：缩小 {changed} 张，保留 {skipped} 张；{before / 1048576:.2f} MB → {after / 1048576:.2f} MB')
        if after >= before:
            log('提示：输出没有变小。某些原图编码更高效，可尝试降低像素上限。')
        return {'changed': changed, 'skipped': skipped, 'before': before, 'after': after}
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
