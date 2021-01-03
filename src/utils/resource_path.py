import sys
import os


def resource_path(relative_path):
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass is not None:
        return os.path.join(meipass, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
