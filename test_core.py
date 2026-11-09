import tempfile
import unittest
from pathlib import Path
from io import BytesIO
import pymupdf as fitz
from PIL import Image, ImageDraw
from core import Settings, compress


class CompressionTests(unittest.TestCase):
    def test_exact_size(self):
        self.assertEqual(Settings().size(6000, 9000), (1333, 2000))
        self.assertEqual(Settings(mode='box').size(6000, 9000), (2000, 3000))
        self.assertEqual(Settings(mode='percent').size(6000, 9000), (2000, 3000))
        self.assertEqual(Settings().size(600, 900), (600, 900))

    def test_document_preservation_and_alpha(self):
        with tempfile.TemporaryDirectory() as folder:
            src, dst = Path(folder) / 'original.pdf', Path(folder) / 'result.pdf'
            image = Image.new('RGB', (600, 900), '#f5ead4')
            draw = ImageDraw.Draw(image)
            draw.rectangle((50, 50, 550, 850), outline='#286b73', width=15)
            draw.text((80, 100), 'Image resize test', fill='black', font_size=40)
            data = BytesIO()
            image.save(data, format='PNG')
            alpha = Image.new('RGBA', (400, 400), (0, 0, 0, 0))
            ImageDraw.Draw(alpha).ellipse((30, 30, 370, 370), fill=(240, 100, 20, 150))
            transparent = BytesIO()
            alpha.save(transparent, format='PNG')
            doc = fitz.open()
            page = doc.new_page(width=400, height=600)
            xref = page.insert_image(fitz.Rect(20, 50, 220, 350), stream=data.getvalue())
            page.insert_text((20, 30), 'Selectable text stays')
            page.insert_image(fitz.Rect(230, 50, 380, 200), stream=transparent.getvalue())
            page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(20, 20, 180, 40), 'uri': 'https://example.com'})
            page = doc.new_page(width=400, height=600)
            page.insert_image(fitz.Rect(20, 50, 220, 350), xref=xref)
            doc.save(src)
            doc.close()
            original = src.read_bytes()
            result = compress(src, dst, Settings(longest=300))
            self.assertEqual(result['changed'], 2)
            self.assertEqual(src.read_bytes(), original)
            with fitz.open(dst) as check:
                self.assertEqual(check.page_count, 2)
                self.assertEqual(check[0].rect, fitz.Rect(0, 0, 400, 600))
                self.assertIn('Selectable text stays', check[0].get_text())
                self.assertEqual(check[0].get_links()[0]['uri'], 'https://example.com')
                self.assertEqual(check[1].get_images()[0][2:4], (200, 300))
                self.assertTrue(any(i[1] > 0 and i[2:4] == (300, 300) for i in check[0].get_images()))
                check[0].get_pixmap().save(str(Path(__file__).parent / 'verification.png'))
            with self.assertRaises(ValueError):
                compress(src, src, Settings())
            with self.assertRaises(ValueError):
                compress(src, dst, Settings())
            cancelled = Path(folder) / 'cancelled.pdf'
            with self.assertRaises(InterruptedError):
                compress(src, cancelled, Settings(), cancelled=lambda: True)
            self.assertFalse(cancelled.exists())

    def test_gui_startup(self):
        import tkinter as tk
        from app import App
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        root.update()
        self.assertEqual(app.mode.get(), 'longest')
        root.destroy()


if __name__ == '__main__':
    unittest.main()
