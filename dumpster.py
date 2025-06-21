#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
dumpster.py - entry point program
"""

import os
import ctypes
from ctypes import (
    c_int, c_char_p, c_uint32, c_size_t, c_ssize_t, c_void_p
)
import struct
import select

# local project imports
from lib.flags import Flags
from lib.inotify import INotify, INotifyWatch

# external 3rd party imports



def main():
    watch_paths = {}
    wds_paths = {}
    base_path = "./testing"

    # convert to fully expanded path
    base_path = os.path.abspath(base_path)
    
    # watch flags for the base directory and all subfolders
    wm = Flags.sum(Flags.IN_CREATE, Flags.IN_DELETE,
                   Flags.IN_ISDIR, Flags.IN_MOVED_TO,
                   Flags.IN_MOVED_FROM)
    evt_size = struct.calcsize('iIII')
    try:
        with INotify(mask=Flags.IN_NONBLOCK()) as inoty:
            watch_paths[base_path] = INotifyWatch(inoty, base_path.encode('utf-8'), wm)

            # do a directory walk and add subdirectories to the watch paths as well
            # todo: learn os path walking again
            print("Walking")
            for (root, dirs, fis) in os.walk(base_path, topdown=True):
                for d in dirs:
                    np = str(os.path.join(root, d))
                    if np not in watch_paths:
                        print(f"Adding '{np}' to watch_paths")
                        watch_paths[np] = INotifyWatch(inoty, np.encode('utf-8'), wm)
            
            loop = True
            poller = select.poll()
            poller.register(inoty.fd, select.POLLIN)
            buf = ctypes.create_string_buffer(4096)
            
            while loop:
                evts = poller.poll(1000)
                
                if not evts:
                    continue
                
                bytes_read = inoty.read(buf, 4096)
                if bytes_read == -1:
                    raise Exception("Read error!")
                elif bytes_read == 0:
                    raise Exception("Inotify FD closed!")
                
                offset = 0
                while offset < bytes_read:
                    oe_size = offset + evt_size
                    evt_header = buf.raw[offset : oe_size]
                    wd_evt, mask, cookie, l = struct.unpack('iIII', evt_header)
                    
                    fname = ""
                    if l > 0:
                        oel_size = oe_size + l
                        name_bytes = buf.raw[oe_size:oel_size].split(b'\0', 1)[0]
                        fname = name_bytes.decode('utf-8', errors='ignore')
                        
                    fp = os.path.join(base_path, fname) if fname else base_path
                        
                    evt_names = Flags.get_event_names(mask)
                    is_dir = bool(Flags.IN_ISDIR() & mask)

                    # categorically, flags fall into two categories, ADD and DEL
                    # create, move_to are ADD
                    # delete, move_from are DEL
                    # editing events should not matter in this system
                    print(f"Action: {evt_names}")
                    if 'IN_CREATE' in evt_names or 'IN_MOVED_TO' in evt_names:
                        if is_dir:
                            print(f"New directory '{fp}'")
                        else:
                            print(f"New file '{fp}'")
                    elif 'IN_DELETE' in evt_names or 'IN_MOVED_FROM' in evt_names:
                        print("Removing thing")
                        if is_dir:
                            print(f"Directory '{fp}' removed")
                        else:
                            print(f"File '{fp}' removed")
                        
                    offset += evt_size + l
    except Exception as e:
        print("*** {e}")
    except KeyboardInterrupt as e:
        print("*** Received STOP message")
    finally:
        # release all known resources
        for path, wd in watch_paths.items():
            wd.close()
        print(">>> Done with this")
        pass
    return

main() if __name__ == "__main__" else None

# end dumpster.py 
