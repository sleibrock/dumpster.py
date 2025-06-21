# Bit flags for inotify

"""
flags.py - all flags for inotify

Values gathered from inotify.h and a C test program
"""

from enum import Enum

class Flags(Enum):
    IN_ACCESS = 0x1 
    IN_MODIFY = 0x2
    IN_ATTRIB = 0x4 
    IN_CLOSE_WRITE = 0x8
    IN_CLOSE_NOWRITE = 0x10
    IN_OPEN = 0x20
    IN_MOVED_FROM = 0x40
    IN_MOVED_TO = 0x80
    IN_CREATE = 0x100
    IN_DELETE = 0x200
    IN_DELETE_SELF = 0x400
    IN_MOVE_SELF = 0x800
    IN_ISDIR = 0x40000000
    IN_UNMOUNT = 0x2000
    IN_Q_OVERFLOW = 0x4000
    IN_CLOEXEC = 0x80000
    IN_NONBLOCK = 0x800

    def __call__(self):
        "Means to convert an Enum to a value easily"
        return self.value

    @classmethod
    def sum(cls, *flags):
        "Add all flags up and return their final bit value"
        s = 0
        for f in flags:
            if isinstance(f, cls):
                s |= f.value
            else:
                raise Exception("What are you doing here")
        return s

    @classmethod
    def get_event_names(cls, mask):
        "Return a list of all flag names for a given mask value"
        return [k.name for k in cls if k.value & mask]
    pass

# end
