[app]
title = Case Battle 3.0
package.name = casesimulator
package.domain = org.hakerdim1
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 3.0.0

requirements = python3==3.11.1,hostpython3==3.11.1,cython==0.29.36,kivy==2.3.0,jnius>=1.4.0,requests,urllib3,certifi

orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.archs = arm64-v8a

android.api = 33
android.minapi = 24
android.ndk = 25b

p4a.branch = master
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
