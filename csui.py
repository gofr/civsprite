#!/usr/bin/env python

import os
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox

import civsprite


FILE_TYPES = [
    ('Test of Time sprite files', '*.spr'),
    ('Text configuration files', '*.txt'),
    ('JSON configuration files', '*.json')
]
TEXT = {
    'title': f'CivSprite {civsprite.__version__} UI',
    'input_button': 'Select input file...',
    'output_button': 'Select output file...',
    'convert_button': 'Convert',
    'exit_button': 'Exit',
    'error_output_exists': 'Output file already exists.',
    'warn_no_files': 'Choose input and output files first.',
    'info_done': 'Done!'
}


class SpriteApplication(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.parent.title(TEXT['title'])
        self.pack()

        self.input = None
        self.output = None

        self.create_widgets()

    def create_widgets(self):
        self.input_button = tk.Button(
            self, text=TEXT['input_button'], command=self.get_input)
        self.input_button.pack(side='top')
        self.output_button = tk.Button(
            self, text=TEXT['output_button'], command=self.get_output)
        self.output_button.pack(side='top')
        self.convert_button = tk.Button(
            self, text=TEXT['convert_button'], command=self.convert)
        self.convert_button.pack(side='left')
        self.quit_button = tk.Button(
            self, text=TEXT['exit_button'], command=self.parent.destroy)
        self.quit_button.pack(side='right')

    def get_input(self):
        self.input = tk.filedialog.askopenfilename(
            parent=self.parent, filetypes=FILE_TYPES)
        if self.input:
            self.input_button['text'] = self.input
        else:
            self.input_button['text'] = TEXT['input_button']

    def get_output(self):
        filename = tk.filedialog.asksaveasfilename(
            parent=self.parent, filetypes=FILE_TYPES, confirmoverwrite=False)
        exists = os.path.exists(filename)
        if filename and not exists:
            self.output = filename
            self.output_button['text'] = self.output
        else:
            self.output = None
            self.output_button['text'] = TEXT['output_button']
            if exists:
                tk.messagebox.showerror(message=TEXT['error_output_exists'])

    def convert(self):
        try:
            if self.input and self.output:
                data = civsprite._input_format(self.input)()
                civsprite._output_format(self.output)(data)
            else:
                tk.messagebox.showwarning(
                    message=TEXT['warn_no_files'])
        except Exception as e:
            message = ''
            while e:
                message += f'{e}\n  '
                e = e.__cause__ or e.__context__
            tk.messagebox.showerror(message=message)
        else:
            tk.messagebox.showinfo(message=TEXT['info_done'])


root = tk.Tk()
app = SpriteApplication(root)
app.mainloop()
