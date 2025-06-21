Dumpster.py - an online file dumpster
---

`dumpster.py` is a web server you can run on your server hardware and serve your images, files and videos(?) online.


## Features

* Upload your files directly using `scp` via SSH, no user management system
* Add comments to files uploaded anonymously (optional)
* Optionally generate indexes for specific folders for easy navigation or sharing

## How it Works

The goal here is to provide a simple system that will look at your file directory and monitor for new file activity. When a new file is uploaded, the server will detect a change on the directory using `inotify` and write the new file entry into a SQLite database. When accessing the file online, it will do a lookup and retrieve the files as well as any associated comments for the file.

```
Asynchronous process model
- inotify listening thread to look for file/directory creates/deletes
- server task to handle inotify events and manage the database
- web server responding to inbound TCP
- serve file requests
- accept comments online (if allowed)
- generate index.html (if allowed)
```

`inotify` is a subsystem specific to Linux, so you will need a Linux host with a compatible `libc` environment for this to work. By leveraging Python's `ctypes` FFI bindings, we can access `inotify` events and logic easily.

## TODOs

* refactor a ton
* `asyncio` and `uvloop` work
* `aiohttp` integrations
* incorporate `jinja2` templating
* `sqlite` integrations
* `json` configurations
* `argparser` CLI settings
* safety considerations
