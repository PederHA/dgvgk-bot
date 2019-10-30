from itertools import count
from typing import Iterable

def get_unique_filename(self, filename: str, *, file_list: Iterable=None) -> str:
    # Increment i until a unique filename is found
    for i in count():
        # we don't need a number if first attempted filename is unique
        i = "" if i==0 else i
        fname = f"{filename}{i}"
        
        if fname not in self.sound_list:
            return fname