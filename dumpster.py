#!/usr/bin/env python
#-*- coding: utf-8 -*-


import os
import ctypes
from ctypes import (
    c_int, c_char_p, c_uint32, c_size_t, c_ssize_t, c_void_p
)
import struct
import select
from enum import Enum

# Bit flags for inotify
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
        return self.value

    def __or__(self, other):
        return self.value | other.value

    @classmethod
    def get_event_names(cls, mask):
        return [k.name for k in cls if k.value & mask]
    pass


# stick INotify interactions in here
class INotify:
    print(">>> Creating inotify bindings ...")

    try:
        _libc = ctypes.CDLL("libc.so.6")
        print(f"Found libc: {_libc}")
    except OSError as e:
        print(f"Error: {e}")
        exit(100)
        pass

    print("Binding signatures on libc")
    _libc.inotify_init1.argtypes = [c_int]
    _libc.inotify_init1.restype = c_int

    _libc.inotify_add_watch.argtypes = [c_int, c_char_p, c_uint32]
    _libc.inotify_add_watch.restype = c_int

    _libc.inotify_rm_watch.argtypes = [c_int, c_int]
    _libc.inotify_rm_watch.restype = c_int

    _libc.read.argtypes = [c_int, c_void_p, c_size_t]
    _libc.read.restype = c_ssize_t

    _libc.close.argtypes = [c_int]
    _libc.close.restype = c_int

    evt_size = struct.calcsize('iIII')
    print("<<< Done with libc.so")

    @classmethod
    def _inotify_init1(cls, mask):
        return cls._libc.inotify_init(mask)

    @classmethod
    def _inotify_add_watch(cls, fd, path, mask):
        return cls._libc.inotify_add_watch(fd, path, mask)

    @classmethod
    def _inotify_rm_watch(cls, fd):
        return

    @classmethod
    def _read(cls, fd, str_p, size_t):
        return cls._libc.read(fd, str_p, size_t)

    @classmethod
    def _close(cls, fd):
        return cls._libc.close(fd)

    def __init__(self, mask=0x0):
        print("Creating inotify ...")
        self.inotify = self._inotify_init1(mask)
        ecode = ctypes.get_errno()
        self.watches = {}

        print(f"inotify: {self.inotify}")
        if self.inotify == -1:
            emsg = os.strerror(ecode)
            raise OSError(f"inotify failed: {emsg}")

        print("Done!!")
        pass

    def watch(self, path, watch_mask):
        # creates a loop that will scan and look for updates
        watch_mask = Flags.IN_CREATE | Flags.IN_ISDIR

        wd = self._inotify_add_watch(
            self.inotify,
            path.encode('utf-8'),
            watch_mask,
        )
        ecode = ctypes.get_errno()

        if wd == -1:
            emsg = os.strerror(ecode)
            self._close(self.inotify)
            raise OSError("Failed to watch. Reason: {emsg}")
        print(f"Watch successful! {wd}")
        
        try:
            poller = select.poll()
            poller.register(self.inotify, select.POLLIN)
            loop_active = True

            # reusable buffer
            buf = ctypes.create_string_buffer(4096)
            while loop_active:
                evts = poller.poll(1000)

                if not evts:
                    continue

                bytes_read = self._read(self.inotify, buf, 4096)

                if bytes_read == -1:
                    raise Exception("Read error!")
                elif bytes_read == 0:
                    print("Inotify closed!")
                    loop_active = False
                    break

                print(f"Bytes read: {bytes_read}")
                offset = 0
                evt_size = self.__class__.evt_size
                while offset < bytes_read:
                    oe_size = offset + evt_size
                    evt_header = buf.raw[offset : oe_size]
                    wd_evt, mask, cookie, l = struct.unpack('iIII', evt_header)

                    fname = ""
                    if l > 0:
                        oel_size = oe_size + l
                        name_bytes = buf.raw[oe_size:oel_size].split(b'\0', 1)[0]
                        fname = name_bytes.decode('utf-8', errors='ignore')

                    fp = os.path.join(path, fname) if fname else path

                    evt_names = Flags.get_event_names(mask)
                    is_dir = bool(Flags.IN_ISDIR() & mask)

                    if 'IN_CREATE' in evt_names and not is_dir:
                        print(f"New file created {fp}")
                    elif 'IN_CREATE' in evt_names and is_dir:
                        print(f"New directory created {fp}")

                    offset += evt_size + l
                    pass
        except Exception as e:
            print("Terrible exception occurred")
            print(e)
        finally:
            print("Closing")
            self.close()
        return

    def close(self):
        print("Goodbye")
        self._libc.close(self.inotify)
        return
    pass

def main():
    instance = INotify(mask=Flags.IN_NONBLOCK())
    instance.watch("./testing", 0x0)
    instance.close()
    return

main() if __name__ == "__main__" else None

# end dumpster.py 
