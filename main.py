import os
import re
import random
import json
import requests
import threading
import time
import math
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.utils import platform
from kivy.properties import NumericProperty

# Проверяем разрешения на Android
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE])

DATABASE_URL = "https://gist.githubusercontent.com/hakerdim1/0ee3bfef3ad74233fa917e1d2da47b2c/raw/database.json"
BASE_IMAGE_URL = "https://raw.githubusercontent.com/hakerdim1/game-images/main/"

if platform != 'android':
    try:
        Window.size = (420, 760)
    except Exception:
        pass

Window.clearcolor = (0.08, 0.08, 0.12, 1)

try:
    from cases_data import CASES_DATABASE as LOCAL_DATABASE
except ImportError:
    LOCAL_DATABASE = {} 

DB = LOCAL_DATABASE
STATUS_TEXT = "Инициализация..."

def get_data_dir():
    app = App.get_running_app()
    return app.user_data_dir if app else "."

def get_images_dir():
    path = os.path.join(get_data_dir(), "images")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_cache_file():
    return os.path.join(get_data_dir(), "database_cache.json")

def get_save_file():
    return os.path.join(get_data_dir(), "savegame.json")

TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def slugify(name):
    out = []
    for ch in name.lower():
        if   ch in TRANSLIT: out.append(TRANSLIT[ch])
        elif ch.isalnum():   out.append(ch)
        else:                out.append('_')
    return re.sub(r'_+', '_', ''.join(out)).strip('_')

def get_image_path(item):
    images_dir = get_images_dir()
    if item.get('image') and os.path.exists(item['image']):
        return item['image']
    slug = slugify(item.get('name', 'item'))
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        p = os.path.join(images_dir, slug + ext)
        if os.path.exists(p):
            return p
    placeholder = "images/placeholder.png" 
    return placeholder if os.path.exists(placeholder) else ''

def left_label(text, **kw):
    lbl = Label(text=text, halign='left', valign='middle', **kw)
    lbl.bind(size=lbl.setter('text_size'))
    return lbl

def get_all_items():
    all_items = []
    for case in DB.values():
        for item in case.get('items', []):
            all_items.append(item)
    unique_items = {item['name']: item for item in all_items}.values()
    return sorted(unique_items, key=lambda x: x['price'])

def download_file(url, local_path):
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"Ошибка {url}: {e}")
        return False

def sync_images():
    global STATUS_TEXT
    images_dir = get_images_dir()
    downloaded = 0
    for case_name, case_data in DB.items():
        case_slug = f"case_{slugify(case_name)}"
        case_exists = any(os.path.exists(os.path.join(images_dir, case_slug + ext)) for ext in ('.png', '.jpg', '.jpeg'))
        if not case_exists:
            for ext in (".png", ".jpg", ".jpeg"):
                if download_file(BASE_IMAGE_URL + case_slug + ext, os.path.join(images_dir, case_slug + ext)):
                    downloaded += 1
                    break

        for item in case_data.get('items', []):
            item_slug = slugify(item.get('name', 'item'))
            item_exists = any(os.path.exists(os.path.join(images_dir, item_slug + ext)) for ext in ('.png', '.jpg', '.jpeg'))
            if not item_exists:
                for ext in (".png", ".jpg", ".jpeg"):
                    if download_file(BASE_IMAGE_URL + item_slug + ext, os.path.join(images_dir, item_slug + ext)):
                        downloaded += 1
                        break
    STATUS_TEXT = f"Картинок скачано: {downloaded}"

def load_database_from_internet(app_instance):
    global DB, STATUS_TEXT
    cache_file = get_cache_file()
    error_msg = None
    try:
        STATUS_TEXT = "Скачивание базы..."
        url_with_no_cache = f"{DATABASE_URL}?t={int(time.time())}"
        headers = {'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}
        r = requests.get(url_with_no_cache, headers=headers, timeout=10)
        r.raise_for_status()
        new_db = r.json()
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(r.text)
        DB = new_db
        STATUS_TEXT = "База обновлена из сети!"
        threading.Thread(target=sync_images, daemon=True).start()
        Clock.schedule_once(lambda dt: app_instance.sm.get_screen('cases').on_enter(), 0)
        return
    except Exception as e:
        error_msg = str(e)
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                DB = json.load(f)
            STATUS_TEXT = f"Ошибка: {error_msg[:20]}. Кэш."
            threading.Thread(target=sync_images, daemon=True).start()
            Clock.schedule_once(lambda dt: app_instance.sm.get_screen('cases').on_enter(), 0)
            return
        except: pass
    STATUS_TEXT = f"Ошибка сети: {error_msg}"

# ============ КАРТОЧКА ============
class Card(BoxLayout):
    def __init__(self, item, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.size_hint = (None, None)
        self.width  = dp(110)
        self.height = dp(145)
        self.padding = dp(6)
        self.spacing = dp(4)
        self.pos_hint = {'center_y': 0.5}
        self.border_thickness = dp(6)

        color = item['color']
        with self.canvas.before:
            Color(*color)
            self.outer = RoundedRectangle(radius=[dp(8)])
            Color(1, 1, 1, 1)
            self.inner = RoundedRectangle(radius=[dp(6)])
        self.bind(pos=self._upd, size=self._upd)

        img_path = get_image_path(item)
        if img_path and os.path.exists(img_path):
            self.add_widget(Image(source=img_path, allow_stretch=True, keep_ratio=True))
        else:
            self.add_widget(Label(text='?', font_size='44sp', color=(0.4, 0.4, 0.4, 1)))

        self.add_widget(Label(text=f"{item['price']:.0f} ₽", font_size='13sp', color=color, bold=True, size_hint_y=None, height=dp(20)))

    def _upd(self, *a):
        self.outer.pos  = self.pos
        self.outer.size = self.size
        off = self.border_thickness
        self.inner.pos  = (self.x + off, self.y + off)
        self.inner.size = (self.width - off * 2, self.height - off * 2)

# ============ СТРОКА ДЛЯ СПИСКОВ ============
class ListRow(ButtonBehavior, BoxLayout):
    def __init__(self, item, on_click, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        self.spacing = dp(8)
        self.padding = dp(6)
        self.item = item
        self.on_click_cb = on_click
        
        with self.canvas.before:
            Color(0.15, 0.15, 0.22, 1)
            self.bg = RoundedRectangle(radius=[dp(4)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        path = get_image_path(item)
        if path and os.path.exists(path):
            self.add_widget(Image(source=path, size_hint_x=None, width=dp(50), allow_stretch=True, keep_ratio=True))
        else:
            self.add_widget(Label(text='?', size_hint_x=None, width=dp(50), font_size='22sp', color=(0.5, 0.5, 0.5, 1)))

        info = BoxLayout(orientation='vertical')
        info.add_widget(left_label(item['name'], font_size='14sp', color=item['color']))
        info.add_widget(left_label(f"{item['price']:.0f} ₽", font_size='11sp', color=(0.6, 0.6, 0.6, 1)))
        self.add_widget(info)
        
    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        
    def on_press(self):
        self.on_click_cb(self.item)

# ============ КОЛЕСО АПГРЕЙДЕРА ============
class UpgraderWheel(Widget):
    chance = NumericProperty(0)
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw, chance=self.redraw, angle=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        
        cx = self.width / 2
        cy = (self.height / 2) + 320 # Ваше смещение сохранено
        r = min(self.width, self.height) / 3

        if r <= 0: return

        end_angle = self.chance * 3.6

        with self.canvas:
            # Темный фон
            Color(0.15, 0.15, 0.2, 1)
            Line(circle=(cx, cy, r), width=dp(10))

            if self.chance > 0:
                # 1. Зеленая зона (рисуем по точкам от 0 до end_angle)
                Color(0.2, 0.9, 0.2, 1)
                green_points = []
                for a in range(0, int(end_angle) + 1, 3):
                    rad = math.radians(a)
                    green_points.extend([cx + r * math.cos(rad), cy + r * math.sin(rad)])
                if green_points:
                    Line(points=green_points, width=dp(10))
                
                # 2. Красная зона (рисуем по точкам от end_angle до 360)
                Color(0.9, 0.2, 0.2, 1)
                red_points = []
                for a in range(int(end_angle), 361, 3):
                    rad = math.radians(a)
                    red_points.extend([cx + r * math.cos(rad), cy + r * math.sin(rad)])
                if red_points:
                    Line(points=red_points, width=dp(10))

            # Центральный кружок
            Color(0.8, 0.8, 0.8, 1)
            Ellipse(pos=(cx - dp(4), cy - dp(4)), size=(dp(8), dp(8)))

            # Стрелка (используем ту же математику, что и для круга)
            Color(1, 1, 1, 1)
            rad = math.radians(self.angle)
            end_x = cx + (r + dp(15)) * math.cos(rad)
            # Убрал минус, чтобы стрелка совпадала с отрисовкой точек
            end_y = cy + (r + dp(15)) * math.sin(rad) 
            Line(points=[cx, cy, end_x, end_y], width=dp(3))
# ============ ЭКРАН 1: КЕЙСЫ ============
class CaseListScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        self.status_lbl = Label(text=STATUS_TEXT, font_size='11sp', color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=dp(20))
        root.add_widget(self.status_lbl)
        root.add_widget(Label(text='КЕЙСЫ', font_size='22sp', bold=True, size_hint_y=None, height=dp(30)))

        self.scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_enter(self):
        self.status_lbl.text = STATUS_TEXT
        self.list_layout.clear_widgets()
        if not DB:
            self.list_layout.add_widget(Label(text="Загрузка базы...", font_size='18sp'))
            return
        for name, data in DB.items():
            self.list_layout.add_widget(self._make_card(name, data))

    def _make_card(self, name, data):
        card = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80), spacing=dp(10), padding=dp(8))
        with card.canvas.before:
            Color(0.15, 0.15, 0.22, 1)
            bg = RoundedRectangle(radius=[dp(8)])
        card.bind(pos=lambda i, v: setattr(bg, 'pos', v), size=lambda i, v: setattr(bg, 'size', v))

        case_slug = f"case_{slugify(name)}"
        icon_path = ""
        for ext in ('.png', '.jpg', '.jpeg'):
            p = os.path.join(get_images_dir(), case_slug + ext)
            if os.path.exists(p):
                icon_path = p
                break
        if not icon_path:
            icon_path = get_image_path(data['items'][-1])
        
        if icon_path and os.path.exists(icon_path):
            card.add_widget(Image(source=icon_path, size_hint_x=None, width=dp(64), allow_stretch=True, keep_ratio=True))
        else:
            card.add_widget(Label(text='📦', size_hint_x=None, width=dp(64), font_size='26sp'))

        info = BoxLayout(orientation='vertical')
        info.add_widget(left_label(name, font_size='15sp', bold=True))
        info.add_widget(left_label(f"{data['desc']}  •  {data['price']:.0f} ₽", font_size='12sp', color=(0.7, 0.7, 0.7, 1)))
        card.add_widget(info)

        btn = Button(text='Открыть', size_hint_x=None, width=dp(90), background_color=(1, 0.4, 0.2, 1), font_size='13sp', bold=True)
        btn.bind(on_press=lambda *a, n=name: self.app.open_case(n))
        card.add_widget(btn)
        return card

# ============ ЭКРАН 2: ИНВЕНТАРЬ ============
class InventoryScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        root.add_widget(Label(text='ИНВЕНТАРЬ', font_size='22sp', bold=True, size_hint_y=None, height=dp(40)))

        self.btn_sell = Button(text='ПРОДАТЬ ВСЁ: 0 ₽', size_hint_y=None, height=dp(50), background_color=(0.2, 0.6, 0.3, 1), bold=True)
        self.btn_sell.bind(on_press=self._sell_all)
        root.add_widget(self.btn_sell)

        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        self.list_layout.clear_widgets()
        if not self.app.inventory:
            self.list_layout.add_widget(Label(text='Инвентарь пуст', font_size='16sp', color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=dp(60)))
            self.btn_sell.disabled = True
            self.btn_sell.text = 'ПРОДАТЬ ВСЁ: 0 ₽'
            return

        total = sum(it['price'] for it in self.app.inventory)
        self.btn_sell.disabled = False
        self.btn_sell.text = f'ПРОДАТЬ ВСЁ: {total:.0f} ₽'

        for it in reversed(self.app.inventory):
            self.list_layout.add_widget(ListRow(it, self._sell_one))

    def _sell_one(self, item):
        if item in self.app.inventory:
            self.app.balance += item['price']
            self.app.inventory.remove(item)
            self.app.update_balance()
            self.app.save_game()
            self.refresh()

    def _sell_all(self, *a):
        if not self.app.inventory: return
        total = sum(it['price'] for it in self.app.inventory)
        self.app.balance += total
        self.app.inventory.clear()
        self.app.update_balance()
        self.app.save_game()
        self.refresh()

# ============ ЭКРАН 3: РУЛЕТКА ============
class OpeningScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.current_case = None
        self.final_prize  = None
        self.is_spinning  = False

        root = FloatLayout()
        header = BoxLayout(size_hint=(1, None), height=dp(40), pos_hint={'top': 1}, spacing=dp(8), padding=(dp(10), 0))
        back = Button(text='<--', size_hint_x=None, width=dp(50), font_size='20sp')
        back.bind(on_press=lambda *a: setattr(self.app.sm, 'current', 'cases'))
        header.add_widget(back)
        self.case_lbl = Label(text='', font_size='16sp', bold=True)
        header.add_widget(self.case_lbl)
        root.add_widget(header)

        roulette_area = FloatLayout(size_hint=(1, None), height=dp(800), pos_hint={'center_y': 0.55})
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=False, bar_width=0)
        self.strip = BoxLayout(orientation='horizontal', size_hint=(None, 1), spacing=dp(6), padding=dp(10))
        self.strip.bind(minimum_width=self.strip.setter('width'))
        self.scroll.add_widget(self.strip)
        roulette_area.add_widget(self.scroll)

        class CenterMarker(Widget):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.size_hint = (None, None)
                self.width = dp(4)
                self.height = dp(150)
                with self.canvas:
                    Color(1, 0.8, 0.1, 1)
                    self.line = Line(width=dp(4))
                self.bind(pos=self._upd, size=self._upd)
            def _upd(self, *a):
                cx = self.x + self.width / 2
                self.line.points = [cx, self.y +250, cx, self.y + 150]

        marker = CenterMarker(pos_hint={'center_x': 0.5, 'center_y': 0.5})
        roulette_area.add_widget(marker)
        root.add_widget(roulette_area)

        self.result_lbl = Label(text='Нажмите ОТКРЫТЬ', font_size='16sp', bold=True, size_hint=(1, None), height=dp(40), pos_hint={'center_x': 0.5, 'center_y': 0.35}, color=(0.8, 0.8, 0.8, 1))
        root.add_widget(self.result_lbl)

        self.btn_open = Button(text='ОТКРЫТЬ', font_size='18sp', bold=True, background_color=(1, 0.3, 0.16, 1), size_hint=(0.9, None), height=dp(60), pos_hint={'center_x': 0.5, 'y': 0.05})
        self.btn_open.bind(on_press=self._spin)
        root.add_widget(self.btn_open)
        self.add_widget(root)

    def open_case(self, case_name):
        self.current_case = DB[case_name]
        self.case_lbl.text = case_name
        self.btn_open.text = f"ОТКРЫТЬ ЗА {self.current_case['price']:.0f} ₽"
        self.result_lbl.text = 'Нажмите ОТКРЫТЬ'
        self.result_lbl.color = (0.8, 0.8, 0.8, 1)
        self.strip.clear_widgets()
        self.app.sm.current = 'opening'

    def _spin(self, *a):
        if self.is_spinning or not self.current_case: return
        case = self.current_case
        items, weights, price = case['items'], case['weights'], case['price']

        if self.app.balance < price:
            self.result_lbl.text  = 'Недостаточно средств!'
            self.result_lbl.color = (1, 0.3, 0.3, 1)
            return

        self.app.balance -= price
        self.app.update_balance()
        self.is_spinning = True
        self.btn_open.disabled = True
        self.result_lbl.text  = 'Крутим...'
        self.result_lbl.color = (0.8, 0.8, 0.8, 1)

        self.final_prize = random.choices(items, weights=weights, k=1)[0]
        self.strip.clear_widgets()
        N_CARDS = 100
        self.winner_index = 90
        for i in range(N_CARDS):
            item = self.final_prize if i == self.winner_index else random.choices(items, weights=weights, k=1)[0]
            self.strip.add_widget(Card(item))

        self.scroll.scroll_x = 0
        Clock.schedule_once(self._animate, 0.15)

    def _animate(self, dt, attempts=0):
        if self.strip.width <= 0 or self.scroll.width <= 0:
            if attempts < 20: Clock.schedule_once(lambda d: self._animate(d, attempts + 1), 0.05)
            else: self._on_anim_done()
            return

        card = self.strip.children[0]
        step = card.width + self.strip.spacing
        pad = self.strip.padding[0]
        viewport, content = self.scroll.width, self.strip.width
        max_scroll = max(1.0, content - viewport)

        card_center = pad + self.winner_index * step + card.width / 2
        card_center += random.uniform(-dp(50), dp(50))
        scroll_pixels = card_center - viewport / 2
        target = max(0.0, min(0.99, scroll_pixels / max_scroll))

        anim = Animation(scroll_x=target, duration=8.0, t='out_quint')
        anim.bind(on_complete=self._on_anim_done)
        anim.start(self.scroll)

    def _on_anim_done(self, *args):
        if self.final_prize:
            self.result_lbl.text  = f"ВЫБИЛИ: {self.final_prize['name']}"
            self.result_lbl.color = self.final_prize['color']
            self.app.inventory.append(self.final_prize.copy())
            self.app.save_game()
        self.is_spinning = False
        self.btn_open.disabled = False

# ============ ЭКРАН 4: АПГРЕЙДЕР ============
class UpgraderScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.source_item = None
        self.target_item = None
        self.is_upgrading = False
        
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        
        # ВЕРХНЯЯ ЧАСТЬ (Фиксированная)
        top_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(430), spacing=dp(5))
        top_layout.add_widget(Label(text='АПГРЕЙДЕР', font_size='20sp', bold=True, size_hint_y=None, height=dp(30)))

        # Слоты
        slots_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(5))
        self.source_btn = Button(text='Ваш скин', background_normal='', background_color=(0.2,0.2,0.3,1))
        self.source_btn.bind(on_press=self.open_inventory_list)
        slots_layout.add_widget(self.source_btn)
        
        slots_layout.add_widget(Label(text='-->', font_size='20sp', size_hint_x=None, width=dp(30)))
        
        self.target_btn = Button(text='Цель', background_normal='', background_color=(0.2,0.2,0.3,1))
        self.target_btn.bind(on_press=self.open_target_list)
        slots_layout.add_widget(self.target_btn)
        top_layout.add_widget(slots_layout)

        # Колесо
        self.wheel = UpgraderWheel(size_hint_y=None, height=dp(250))
        top_layout.add_widget(self.wheel)

        # Шанс и кнопка
        self.chance_lbl = Label(text='Шанс: -- %', font_size='18sp', bold=True, color=(0.7,0.7,0.7,1), size_hint_y=None, height=dp(25))
        top_layout.add_widget(self.chance_lbl)

        self.btn_upgrade = Button(text='УЛУЧШИТЬ', font_size='16sp', bold=True, background_color=(1, 0.6, 0.1, 1), size_hint_y=None, height=dp(50), disabled=True)
        self.btn_upgrade.bind(on_press=self.do_upgrade)
        top_layout.add_widget(self.btn_upgrade)
        
        root.add_widget(top_layout)

        # НИЖНЯЯ ЧАСТЬ (Список)
        self.list_scroll = ScrollView(size_hint_y=1)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.list_scroll.add_widget(self.list_layout)
        root.add_widget(self.list_scroll)

        self.add_widget(root)

    def on_enter(self):
        self.source_item = None
        self.target_item = None
        self.wheel.angle = 0
        self.wheel.chance = 0
        self.update_ui()
        self.open_inventory_list()

    def open_inventory_list(self, *args):
        if self.is_upgrading: return
        self.list_layout.clear_widgets()
        if not self.app.inventory:
            self.list_layout.add_widget(Label(text="Инвентарь пуст", size_hint_y=None, height=dp(50)))
            return
        
        for item in self.app.inventory:
            self.list_layout.add_widget(ListRow(item, self.select_source))

    def select_source(self, item):
        self.source_item = item
        self.target_item = None
        self.wheel.angle = 0
        self.update_ui()
        self.open_target_list()

    def open_target_list(self, *args):
        if not self.source_item or self.is_upgrading: return
            
        self.list_layout.clear_widgets()
        all_items = get_all_items()
        targets = [i for i in all_items if i['price'] > self.source_item['price']]
        
        if not targets:
            self.list_layout.add_widget(Label(text="Нет предметов дороже", size_hint_y=None, height=dp(50)))
            return
            
        for item in targets:
            self.list_layout.add_widget(ListRow(item, self.select_target))

    def select_target(self, item):
        self.target_item = item
        self.update_ui()

    def update_ui(self):
        if self.source_item:
            self.source_btn.text = f"{self.source_item['name']}\n{self.source_item['price']:.0f} ₽"
            self.source_btn.background_color = self.source_item['color']
        else:
            self.source_btn.text = 'Ваш скин'
            self.source_btn.background_color = (0.2,0.2,0.3,1)

        if self.target_item:
            self.target_btn.text = f"{self.target_item['name']}\n{self.target_item['price']:.0f} ₽"
            self.target_btn.background_color = self.target_item['color']
        else:
            self.target_btn.text = 'Цель'
            self.target_btn.background_color = (0.2,0.2,0.3,1)

        if self.source_item and self.target_item:
            chance = (self.source_item['price'] / self.target_item['price']) * 100
            chance = min(chance, 90.0)
            self.chance_lbl.text = f"Шанс: {chance:.1f} %"
            self.chance_lbl.color = (1, 0.8, 0.2, 1)
            self.wheel.chance = chance
            self.btn_upgrade.disabled = False
        else:
            self.chance_lbl.text = "Шанс: -- %"
            self.chance_lbl.color = (0.7,0.7,0.7,1)
            self.wheel.chance = 0
            self.btn_upgrade.disabled = True

    def do_upgrade(self, *args):
        if not self.source_item or not self.target_item or self.is_upgrading: return
        
        self.is_upgrading = True
        self.btn_upgrade.disabled = True
        self.source_btn.disabled = True
        self.target_btn.disabled = True
        
        chance = min((self.source_item['price'] / self.target_item['price']) * 100, 90.0)
        
        # 1. Определяем исход (успех или провал)
        is_success = random.uniform(0, 100) <= chance
        
        # 2. Выбираем угол так, чтобы он ГАРАНТИРОВАННО попадал в нужную зону
        if is_success:
            # От 0 до конца зеленой зоны
            target_angle = random.uniform(0, chance * 3.6)
        else:
            # От конца зеленой зоны до 360
            target_angle = random.uniform(chance * 3.6, 360)
            
        # 3. Добавляем 5 полных оборотов для эффекта
        final_angle = target_angle + (360 * 5)
        
        self.chance_lbl.text = "Крутим..."
        self.chance_lbl.color = (1, 1, 1, 1)
        
        # 4. Запускаем анимацию
        anim = Animation(angle=final_angle, duration=4.0, t='out_expo')
        anim.bind(on_complete=lambda *a: self._resolve_upgrade(is_success))
        anim.start(self.wheel)
    def _resolve_upgrade(self, is_success):
        if is_success:
            self.app.inventory.remove(self.source_item)
            self.app.inventory.append(self.target_item.copy())
            self.chance_lbl.text = "УСПЕХ!"
            self.chance_lbl.color = (0.2, 1, 0.2, 1)
        else:
            self.app.inventory.remove(self.source_item)
            self.chance_lbl.text = "ПРОВАЛ!"
            self.chance_lbl.color = (1, 0.2, 0.2, 1)
            
        self.app.save_game()
        
        def reset_ui(dt):
            self.is_upgrading = False
            self.source_btn.disabled = False
            self.target_btn.disabled = False
            self.source_item = None
            self.target_item = None
            self.wheel.angle = 0
            self.update_ui()
            self.open_inventory_list()
            
        Clock.schedule_once(reset_ui, 3.0)

# ==============================================================
# ПРИЛОЖЕНИЕ
# ==============================================================
class CaseApp(App):
    def build(self):
        self.balance = 5000.0
        self.inventory = []
        self.load_game()

        root = BoxLayout(orientation='vertical')

        top = BoxLayout(size_hint_y=None, height=dp(45), padding=(dp(12), 0))
        self.lbl_bal = left_label('', font_size='18sp', bold=True, color=(1, 0.85, 0.3, 1))
        top.add_widget(self.lbl_bal)
        root.add_widget(top)
        self.update_balance()

        self.sm = ScreenManager()
        self.sm.add_widget(CaseListScreen(app=self, name='cases'))
        self.sm.add_widget(InventoryScreen(app=self, name='inventory'))
        self.sm.add_widget(UpgraderScreen(app=self, name='upgrader'))
        self.open_screen = OpeningScreen(app=self, name='opening')
        self.sm.add_widget(self.open_screen)
        root.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(2))
        btn_cases = Button(text='Кейсы', font_size='14sp', bold=True, background_color=(0.2, 0.4, 0.8, 1))
        btn_upg = Button(text='Апгрейдер', font_size='14sp', bold=True, background_color=(0.8, 0.4, 0.2, 1))
        btn_inv = Button(text='Инвентарь', font_size='14sp', bold=True, background_color=(0.2, 0.6, 0.3, 1))
        
        btn_cases.bind(on_press=lambda *a: setattr(self.sm, 'current', 'cases'))
        btn_upg.bind(on_press=lambda *a: setattr(self.sm, 'current', 'upgrader'))
        btn_inv.bind(on_press=lambda *a: setattr(self.sm, 'current', 'inventory'))
        
        nav.add_widget(btn_cases)
        nav.add_widget(btn_upg)
        nav.add_widget(btn_inv)
        root.add_widget(nav)

        threading.Thread(target=load_database_from_internet, args=(self,), daemon=True).start()

        return root

    def update_balance(self):
        self.lbl_bal.text = f'Баланс: {self.balance:.0f} ₽'

    def open_case(self, case_name):
        self.open_screen.open_case(case_name)
        
    def save_game(self):
        data = {"balance": self.balance, "inventory": self.inventory}
        with open(get_save_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    def load_game(self):
        save_path = get_save_file()
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 5000.0)
                    self.inventory = data.get("inventory", [])
            except Exception as e:
                print("Ошибка загрузки сохранения:", e)

if __name__ == '__main__':
    CaseApp().run()
