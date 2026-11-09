import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core import Settings, compress


class App:
    def __init__(self, root):
        self.root = root
        root.title('PDF 图片像素压缩')
        root.geometry('820x850')
        root.minsize(740, 850)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.files = []
        self.busy = False
        self.output = tk.StringVar()
        self.mode = tk.StringVar(value='longest')
        self.longest = tk.StringVar(value='2000')
        self.percent = tk.StringVar(value='33.333333')
        self.width = tk.StringVar(value='2000')
        self.height = tk.StringVar(value='3000')
        self.quality = tk.StringVar(value='90')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='PDF 图片像素压缩', font=('Microsoft YaHei UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='按实际像素缩小内部图片，页面尺寸保持不变。所有文件在本机处理。').pack(anchor='w', pady=(4, 16))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.add = ttk.Button(row, text='添加 PDF 文件…', command=self.pick)
        self.add.pack(side='left')
        self.clear = ttk.Button(row, text='清空列表', command=self.clear_files)
        self.clear.pack(side='left', padx=8)
        self.list = tk.Listbox(frame, height=4, font=('Microsoft YaHei UI', 10))
        self.list.pack(fill='x', pady=8)
        settings = ttk.LabelFrame(frame, text='图片缩小方式', padding=12)
        settings.pack(fill='x', pady=8)
        self.fields = []
        for r, (value, title, variables) in enumerate([
            ('longest', '最长边不超过', [(self.longest, '像素')]),
            ('percent', '宽高缩放至原图的', [(self.percent, '%')]),
            ('box', '限制在宽高范围内', [(self.width, '×'), (self.height, '像素')]),
        ]):
            button = ttk.Radiobutton(settings, text=title, variable=self.mode, value=value, command=self.update_fields)
            button.grid(row=r, column=0, sticky='w', pady=5)
            self.fields.append((button, None))
            for i, (variable, suffix) in enumerate(variables):
                entry = ttk.Entry(settings, textvariable=variable, width=12)
                entry.grid(row=r, column=i * 2 + 1, padx=8)
                ttk.Label(settings, text=suffix).grid(row=r, column=i * 2 + 2, sticky='w')
                self.fields.append((entry, value))
        ttk.Label(settings, text='始终保持宽高比例，不放大小图片。4000×6000 → 最长边 2000 → 1333×2000。').grid(row=3, column=0, columnspan=5, sticky='w', pady=(8, 0))
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        ttk.Label(row, text='JPEG 质量（1～100）').pack(side='left')
        self.qentry = ttk.Entry(row, textvariable=self.quality, width=8)
        self.qentry.pack(side='left', padx=10)
        ttk.Label(row, text='建议 90；透明图片使用 PNG 保留透明度。').pack(side='left')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=6)
        ttk.Label(row, text='输出文件夹').pack(side='left')
        self.outentry = ttk.Entry(row, textvariable=self.output)
        self.outentry.pack(side='left', fill='x', expand=True, padx=10)
        self.outbutton = ttk.Button(row, text='选择…', command=self.pick_output)
        self.outbutton.pack(side='left')
        ttk.Label(frame, text='留空则保存到原文件旁；自动添加“_像素压缩”后缀，原文件保留。').pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=14)
        self.start = ttk.Button(row, text='开始压缩', command=self.run)
        self.start.pack(side='left')
        self.cancel = ttk.Button(row, text='取消', state='disabled', command=self.stop.set)
        self.cancel.pack(side='left', padx=8)
        ttk.Button(row, text='打开输出文件夹', command=self.open_output).pack(side='right')
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x')
        self.log = tk.Text(frame, height=9, wrap='word', font=('Microsoft YaHei UI', 9), state='disabled')
        self.log.pack(fill='both', expand=True, pady=(8, 0))
        self.update_fields()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)

    def update_fields(self):
        for widget, mode in self.fields:
            widget.configure(state='disabled' if self.busy or (mode and mode != self.mode.get()) else 'normal')

    def pick(self):
        for file in filedialog.askopenfilenames(filetypes=[('PDF 文件', '*.pdf')]):
            if file not in self.files:
                self.files.append(file)
                self.list.insert('end', file)

    def clear_files(self):
        self.files.clear()
        self.list.delete(0, 'end')

    def pick_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output.set(path)

    def open_output(self):
        path = self.output.get().strip() or (str(Path(self.files[0]).parent) if self.files else '')
        if path and Path(path).is_dir():
            os.startfile(path)

    def set_busy(self, value):
        self.busy = value
        for widget in [self.add, self.clear, self.qentry, self.outentry, self.outbutton, self.start]:
            widget.configure(state='disabled' if value else 'normal')
        self.cancel.configure(state='normal' if value else 'disabled')
        self.update_fields()
        self.progress.start(12) if value else self.progress.stop()

    def run(self):
        if not self.files:
            messagebox.showinfo('添加文件', '请先添加一个或多个 PDF 文件。')
            return
        try:
            settings = Settings(self.mode.get(), int(self.longest.get()), float(self.percent.get()), int(self.width.get()), int(self.height.get()), int(self.quality.get()))
            settings.validate()
        except ValueError as exc:
            messagebox.showerror('参数错误', f'请检查输入的数字。\n{exc}')
            return
        self.stop.clear()
        self.set_busy(True)
        files, output = self.files[:], self.output.get().strip()
        threading.Thread(target=self.work, args=(files, output, settings), daemon=True).start()

    def work(self, files, output, settings):
        success = failures = 0
        for file in files:
            if self.stop.is_set():
                break
            source = Path(file)
            directory = Path(output) if output else source.parent
            target = directory / f'{source.stem}_像素压缩.pdf'
            i = 2
            while target.exists():
                target = directory / f'{source.stem}_像素压缩_{i}.pdf'
                i += 1
            self.events.put(('log', f'\n正在处理：{source.name}'))
            try:
                compress(source, target, settings, lambda text: self.events.put(('log', text)), self.stop.is_set)
                success += 1
                self.events.put(('log', f'已保存：{target}'))
            except InterruptedError as exc:
                self.events.put(('log', str(exc)))
                break
            except Exception as exc:
                failures += 1
                self.events.put(('log', f'处理失败：{exc}'))
        self.events.put(('done', f'成功 {success} 个，失败 {failures} 个' + ('；已取消后续处理' if self.stop.is_set() else '')))

    def poll(self):
        while not self.events.empty():
            kind, text = self.events.get()
            self.log.configure(state='normal')
            self.log.insert('end', text + '\n')
            self.log.see('end')
            self.log.configure(state='disabled')
            if kind == 'done':
                self.set_busy(False)
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('正在处理', '请先点击取消，等待当前图片处理完成后再关闭。')
        else:
            self.root.destroy()


if __name__ == '__main__':
    App(tk.Tk()).root.mainloop()
