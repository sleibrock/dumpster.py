#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
dumpster.py - entry point program
"""

import os
import struct
from ctypes import create_string_buffer
from select import poll as Poller, POLLIN as sel_POLLIN

# local project imports
from lib.flags import Flags
from lib.inotify import INotify, INotifyWatch

# external 3rd party imports



def main():
    wd_data = {} # WD => INotifyWatch
    paths_hooked = {} # String => WD
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
            base_watch = INotifyWatch(inoty, base_path, wm)
            wd_data[base_watch.fd] = base_watch
            paths_hooked[base_path] = base_watch.fd 

            # do a directory walk and add subdirectories to the watch paths as well
            print("Walking")
            for (root, dirs, fis) in os.walk(base_path, topdown=True):
                for d in dirs:
                    np = str(os.path.join(root, d))
                    if np not in paths_hooked:
                        print(f"Adding '{np}' to watch_paths")
                        new_watch = INotifyWatch(inoty, np, wm)
                        wd_data[new_watch.fd] = new_watch
                        paths_hooked[np] = new_watch.fd 
            
            loop = True
            poller = Poller()
            poller.register(inoty.fd, sel_POLLIN)
            buf = create_string_buffer(4096)
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
                    # wd_evt is the WD identifier for the file path?

                    print("File event happened in:")
                    evt_basepath = wd_data[wd_evt].path

                    if wd_evt not in wd_data:
                        print(f"{wd_evt} not in {list(wd_data.keys())}")
                        raise Exception("Some illegal ass state just happened")

                    fname = ""
                    if l > 0:
                        oel_size = oe_size + l
                        name_bytes = buf.raw[oe_size:oel_size].split(b'\0', 1)[0]
                        fname = name_bytes.decode('utf-8', errors='ignore')
                        
                    fp = os.path.join(evt_basepath, fname) if fname else evt_basepath
                        
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
                            np = os.path.join(fp)
                            nwd = INotifyWatch(inoty, fp, wm)
                            wd_data[nwd.fd] = nwd
                            paths_hooked[fp] = nwd.fd

                            print("Walking new directory (inotify won't do this)")
                            for (root, dirs, fis) in os.walk(fp, topdown=True):
                                for d in dirs:
                                    np = str(os.path.join(root, d))
                                    if np not in paths_hooked:
                                        print(f"Adding '{np}' to watch_paths")
                                        new_watch = INotifyWatch(inoty, np, wm)
                                        wd_data[new_watch.fd] = new_watch
                                        paths_hooked[np] = new_watch.fd 
                        else:
                            print(f"New file '{fp}'")
                    elif 'IN_DELETE' in evt_names or 'IN_MOVED_FROM' in evt_names:
                        # a file or dir in WD got removed
                        # check if the file was tracked and close the separate WD if so
                        if is_dir:
                            if fp in paths_hooked:
                                # close the WD and remove the path entry
                                print(f"{fp} is being watched, removing it")
                                target_wd = paths_hooked.get(fp)
                                wd_data[target_wd].close()
                                del paths_hooked[fp]
                                del wd_data[target_wd]
                            else:
                                raise Exception("Illegal ass state again???")
                        else:
                            print(f"File '{fp}' removed")
                        
                    offset += evt_size + l
    except Exception as e:
        print(f"!!!*** {e} ***!!!")
    except KeyboardInterrupt as e:
        print("*** Received STOP message")
    finally:
        # release all known resources
        for path, wd in wd_data.items():
            wd.close()
        print(">>> Done with this")
        pass
    return

main() if __name__ == "__main__" else None

# end dumpster.py 
