[app]
title = Case Battle 3.0
package.name = casesimulator
package.domain = org.hakerdim1
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# Добавляем jnius, requests и certifi для работы сети и Android API
requirements = python3,kivy==2.3.0,jnius>=1.4.0,requests,urllib3,certifi

orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.archs = arm64-v8a

# Проверенная связка API и NDK
android.api = 33
android.minapi = 24
android.ndk = 25b

p4a.branch = develop
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
