[app]
title = Case Battle 3.0
package.name = casesimulator
package.domain = org.hakerdim1
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# Оставляем стабильную версию Python и Cython
requirements = python3==3.11.1,hostpython3==3.11.1,cython==0.29.36,kivy==2.3.0,requests,urllib3,certifi

orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.archs = arm64-v8a

# Указываем стабильные версии API и NDK
android.api = 33
android.minapi = 24
android.ndk = 25b

# Переключаем ветку python-for-android на develop (решает многие проблемы с Gradle)
p4a.branch = develop

android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
