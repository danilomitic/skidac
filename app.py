# -*- coding: utf-8 -*-
"""Skidac — ulazna tacka. Logika je u paketu skidac/."""

import ctypes
import traceback
import tkinter as tk
from tkinter import messagebox


def ostri_tekst():
    """Bez ovoga je sve mutno na ekranima sa skaliranjem preko 100%."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    ostri_tekst()
    from skidac.gui import App
    App().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Greška", traceback.format_exc()[-1500:])
        except Exception:
            pass
