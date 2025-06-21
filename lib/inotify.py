# inotify.py

"""
inotify.py - mini library to deal with inotify procedures

Broken down into three classes

* INotifyFFI - class to bind libc interactions
* INotify - an instance of INotify's FD for safety
* INotifyWatch - an instance of a watcher FD for safety
"""


import os
import ctypes
from ctypes import (
    c_int, c_char_p, c_uint32, c_size_t, c_ssize_t, c_void_p
)


class INotifyFFI(object):
    """
    INotifyFFI is the libc bindings for the inotify subsystem
    the libc needs to be loaded through ctypes as a DLL
    and methods should be safely encapsulated at this point
    to account as much as possible for type safety.

    Every FFI method from libc will have an equal parts
    method in Python to bind it in place for access in
    other parts of the project. ie. inotify_init1() will
    become INotifyFFI.init1() in Python.

    The FFI here will be bound to a class instead
    of a single object for simplicity. The libc connection
    will be bound behind a private variable to prevent
    misuse of it as much as (feasibly) possible.
    """
    __slots__ = []

    print(">>> Creating inotify bindings ...")

    try:
        __libc = ctypes.CDLL("libc.so.6")
        print(f"Found libc: {__libc}")
    except OSError as e:
        print(f"Error: {e}")
        exit(100)
        pass

    print("Binding signatures on libc")
    __libc.inotify_init1.argtypes = [c_int]
    __libc.inotify_init1.restype = c_int

    __libc.inotify_add_watch.argtypes = [c_int, c_char_p, c_uint32]
    __libc.inotify_add_watch.restype = c_int

    __libc.inotify_rm_watch.argtypes = [c_int, c_int]
    __libc.inotify_rm_watch.restype = c_int

    __libc.read.argtypes = [c_int, c_void_p, c_size_t]
    __libc.read.restype = c_ssize_t

    __libc.close.argtypes = [c_int]
    __libc.close.restype = c_int

    print("<<< Done with libc.so")

    def __init__(self):
        raise Exception("!!!Do not instantiate!!!")

    @classmethod
    def init1(cls, mask):
        return cls.__libc.inotify_init(mask)

    @classmethod
    def add_watch(cls, fd, path, mask):
        return cls.__libc.inotify_add_watch(fd, path, mask)

    @classmethod
    def rm_watch(cls, fd, wd):
        return cls.__libc.inotify_rm_watch(fd, wd)

    @classmethod
    def read(cls, fd, str_p, size_t):
        return cls.__libc.read(fd, str_p, size_t)

    @classmethod
    def close(cls, fd):
        return cls.__libc.close(fd)
    pass


class CanFFIError(object):
    "Simple base class to do some common C error work"
    def error(self):
        errc = ctypes.get_errno()
        msg = os.strerror(errc)
        return f"{errc} {msg}"


class FileDescriptor(CanFFIError):
    "Generalized file descriptor logic for safety"
    __slots__ = ['fd']
    def __init__(self, fd):
        self.fd = fd
        return

    def close(self):
        return INotifyFFI.close(self.fd)
    pass
        

class INotify(FileDescriptor):
    """
    Main FD for an INotify instance

    To be used with `with INotify(args) as var:`
    """
    def __init__(self, mask):
        print("You've initiated Inotify")
        fd = INotifyFFI.init1(mask)
        if fd == -1:
            msg = self.error()
            self.close()
            raise Exception(msg)
        
        super().__init__(fd)
        return

    def __enter__(self):
        print(">>> You've entered inotify")
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        print(">>> Now closing inotify")
        return self.close()

    def read(self, buf, buf_size):
        "Passing the FD into the FFI read() function"
        return INotifyFFI.read(self.fd, buf, buf_size)
    pass


class INotifyWatch(FileDescriptor):
    """
    FD class for Watchers that monitor a single directory
    Each directory to watch will need it's own respective FD
    """
    __slots__ = ["fd", "inoty"]
    def __init__(self, inoty, path, mask):
        fd = INotifyFFI.add_watch(inoty.fd, path, mask)
        if fd == -1:
            msg = self.error()
            raise Exception(msg)

        super().__init__(fd)
        self.inoty = inoty
        return

    def close(self):
        "Needs inotify_rm_watch() instead of close()"
        print(f"Closing watcher {self.fd}")
        return INotifyFFI.rm_watch(self.inoty.fd, self.fd)
    pass


# end
