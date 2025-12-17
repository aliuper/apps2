[app]

title = AliBaba
package.name = alibaba
package.domain = org.alibaba

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,gif,svg,json,txt

version = 0.1

requirements = python3,kivy==2.3.1,kivymd==1.2.0,requests==2.32.3,python-dateutil==2.9.0.post0,androidstorage4kivy==0.1.3

orientation = portrait
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b

android.accept_sdk_license = True

# (str) Python-for-android bootstrap
p4a.bootstrap = sdl2

# (str) The main entry point of the application
entrypoint = main.py

[buildozer]
log_level = 2
warn_on_root = 1
