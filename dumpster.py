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
import asyncio
import aiofiles
from aiohttp import web
import jinja2
from jinja2 import Environment, PackageLoader, select_autoescape


base_path = "./testing"

# convert to fully expanded path
base_path = os.path.abspath(base_path)

class AppServer:

    # extensions supported (for now)
    image_types = ["jpg", "jpeg", "png", "gif", "webp", "tiff"]
    text_types = ["txt", "md", "c", "cpp", "py", "rkt", "lisp", "rs"]
    movie_types = ["webm", "mp4"]

    # files used to present files
    templates = ["index", "text_view", "img_view", "movie_view"]

    def __init__(self, base_path):
        self.jinja = Environment(
            loader=PackageLoader("dumpster"),
            autoescape=select_autoescape(),
        )
        self.base_path = base_path
        self.tmpls = {t: self.jinja.get_template(f"{t}.html") for t in self.templates}
        self.not_found = web.Response(text="404 File Not Found")
        return

    def get_typeof(self, path_to_check):
        p = os.path.join(self.base_path, path_to_check)
        if os.path.isdir(p):
            return 'DIR'
        if os.path.isfile(p):
            return 'FI'
        return None 

    def get_template_for(self, res):
        # determine template for the resource type
        # return None if no match found for the extension type
        ext = res.strip().split(".")[-1].lower()
        if ext in self.text_types:
            return self.tmpls.get("text_view", None), True
        if ext in self.image_types:
            return self.tmpls.get("img_view", None), False
        if ext in self.movie_types:
            return self.tmpls.get("movie_view", None), False
        return None, False
            
    async def resource_handler(self, request):
        res = request.match_info.get('resource', '')
        res_path = os.path.join(self.base_path, res)
        typeof = self.get_typeof(res_path)
        if typeof == 'FI':
            f = web.FileResponse(path=res_path)
            f.enable_compression() # turn on compression (req dictates)
            return f
        return self.not_found

    async def view_handler(self, request):
        """
        Accept a request for a resource
        Yield a valid response if the resource exists
        Yield 404 otherwise
        """
        res = request.match_info.get('resource', '')
        res_url = os.path.join('/res/', res)
        res_path = os.path.join(self.base_path, res)
        print(f"Requested resource: {res}")
        print(f"Resolved url: {res_url}")
        print(f"Target res path: {res_path}")

        typeof = self.get_typeof(res)
        if not typeof:
            return self.not_found

        if typeof == 'DIR':
            # generate an index of this Dir if allowed
            # if not, bail out and 404!!!
            raw_files = os.listdir(res_path)
            if 'NOINDEX' in raw_files:
                return self.not_found

            subfolders = [
                {'name': f, 'url': os.path.join("/view", res, f)}
                 for f in raw_files if os.path.isdir(os.path.join(res_path, f))
            ]
            files = [
                {'name': f, 'url': os.path.join("/view", res, f)}
                for f in raw_files if os.path.isfile(os.path.join(res_path, f))
            ]
            
            tmpl = self.tmpls.get("index", None)
            if not tmpl:
                print("Why are we here?")
                return self.not_found

            if res.strip() == "":
                res = "/"
            text = tmpl.render(directory=res, files=files, folders=subfolders)
            return web.Response(content_type="text/html", text=text)

        tmpl, is_text = self.get_template_for(res)
        if not tmpl:
            return self.not_found

        text = "404 File Not Found"
        if is_text:
            # load the text (aiofiles needed???)
            text_path = os.path.join(self.base_path, res)
            async with aiofiles.open(text_path, 'r') as fi:
                loaded_txt = await fi.read()
            text = tmpl.render(filename=res, text=loaded_txt)
        else:
            text = tmpl.render(filename=res, url=res_url)
        return web.Response(content_type='text/html', text=text)
    pass


def main2():
    "Second iteration of main2() for aiohttp now"
    app = web.Application()
    dumpster = AppServer(base_path)

    #app['chuck'] = "I can chuck what I want in here????"
    #app.on_startup.append(test_startup)

    # bind the routes to the app service
    app.router.add_get('/res/{resource:.*}', dumpster.resource_handler)
    app.router.add_get('/view/{resource:.*}', dumpster.view_handler)

    web.run_app(app, host='0.0.0.0', port=8811)
    pass

def main():
    "Old code to port to an asyncio system"

    wd_data = {} # WD => INotifyWatch
    paths_hooked = {} # String => WD
    
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

main2() if __name__ == "__main__" else None

# end dumpster.py 
