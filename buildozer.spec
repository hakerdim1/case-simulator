[app]
# Название, которое будет на телефоне
title = Case Battle 3.0
# Имя файла (латиницей, без пробелов)
package.name = casesimulator
package.domain = org.hakerdim1

source.dir = .
# Обязательно добавляем json, чтобы сохранения работали, и png для картинок
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# Библиотеки для игры и для работы интернета
requirements = python3,kivy==2.3.0,requests,urllib3,certifi

orientation = portrait
fullscreen = 0
# Разрешение на выход в интернет
android.permissions = INTERNET
# Современная архитектура и ветка p4a
android.archs = arm64-v8a
p4a.branch = develop
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
