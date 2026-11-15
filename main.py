import os
import re
import random
import json
import requests # 👈 Заменили urllib на requests
import threading
import time
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
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.core.window import Window
from kivy.utils import platform

# Проверяем разрешения на Android (Интернет)
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE])

# =========================================================================
DATABASE_URL = "https://gist.githubusercontent.com/hakerdim1/0ee3bfef3ad74233fa917e1d2da47b2c/raw/database.json"
BASE_IMAGE_URL = "https://raw.githubusercontent.com/hakerdim1/game-images/main/"
# =========================================================================

# На ПК задаем размер окна, на телефоне - нет!
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

# Функции для получения правильных путей (Android запрещает писать в корень)
def get_data_dir():
    app = App.get_running_app()
    if app:
        return app.user_data_dir
    return "."

def get_images_dir():
    path = os.path.join(get_data_dir(), "images")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_cache_file():
    return os.path.join(get_data_dir(), "database_cache.json")

def get_save_file():
    return os.path.join(get_data_dir(), "savegame.json")

# ============ ХЕЛПЕРЫ ДЛЯ КАРТИНОК ============
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
    # Плейсхолдер должен лежать в папке с игрой (в assets), поэтому ищем его отдельно
    placeholder = "images/placeholder.png" 
    return placeholder if os.path.exists(placeholder) else ''

def left_label(text, **kw):
    lbl = Label(text=text, halign='left', valign='middle', **kw)
    lbl.bind(size=lbl.setter('text_size'))
    return lbl

# ============ СИСТЕМА СКАЧИВАНИЯ (с обходом ошибок SSL на Android) ============
def download_file(url, local_path):
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"Ошибка скачивания {url}: {e}")
        return False

def sync_images():
    global STATUS_TEXT
    print("Начинаем проверку картинок...")
    images_dir = get_images_dir()
    downloaded = 0
    
    for case_name, case_data in DB.items():
        # Обложки кейсов
        case_slug = f"case_{slugify(case_name)}"
        case_exists = any(os.path.exists(os.path.join(images_dir, case_slug + ext)) for ext in ('.png', '.jpg', '.jpeg'))
        if not case_exists:
            for ext in (".png", ".jpg", ".jpeg"):
                if download_file(BASE_IMAGE_URL + case_slug + ext, os.path.join(images_dir, case_slug + ext)):
                    downloaded += 1
                    break

        # Предметы
        for item in case_data.get('items', []):
            item_slug = slugify(item.get('name', 'item'))
            item_exists = any(os.path.exists(os.path.join(images_dir, item_slug + ext)) for ext in ('.png', '.jpg', '.jpeg'))
            if not item_exists:
                for ext in (".png", ".jpg", ".jpeg"):
                    if download_file(BASE_IMAGE_URL + item_slug + ext, os.path.join(images_dir, item_slug + ext)):
                        downloaded += 1
                        break
    STATUS_TEXT = f"Картинок скачано: {downloaded}"
    print("Скачивание картинок завершено!")

# ============ ОБНОВЛЕННАЯ ЗАГРУЗКА БАЗЫ (ОБХОД КЭША) ============
def load_database_from_internet(app_instance):
    global DB, STATUS_TEXT
    cache_file = get_cache_file()
    try:
        STATUS_TEXT = "Скачивание базы..."
        print("Пытаемся скачать базу...")
        
        # 👇 МАГИЯ: добавляем время к ссылке, чтобы GitHub не отдавал старую версию 👇
        url_with_no_cache = f"{DATABASE_URL}?t={int(time.time())}"
        headers = {'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}
        
        r = requests.get(url_with_no_cache, headers=headers, timeout=10)
        r.raise_for_status()
        
        new_db = r.json()
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(r.text)
        
        DB = new_db
        STATUS_TEXT = "База обновлена из сети!"
        print("База успешно обновлена!")
        
        threading.Thread(target=sync_images, daemon=True).start()
        Clock.schedule_once(lambda dt: app_instance.sm.get_screen('cases').on_enter(), 0)
        return
    except Exception as e:
        STATUS_TEXT = f"Ошибка сети: {str(e)[:20]}"
        print("Не удалось скачать базу:", e)
    
    if os.path.exists(cache_file):
        try:
            STATUS_TEXT = "Загрузка из кэша..."
            print("Загружаем базу из кэша...")
            with open(cache_file, 'r', encoding='utf-8') as f:
                DB = json.load(f)
            threading.Thread(target=sync_images, daemon=True).start()
            Clock.schedule_once(lambda dt: app_instance.sm.get_screen('cases').on_enter(), 0)
            return
        except Exception as e:
            print("Ошибка чтения кэша:", e)

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

# ============ СТРОКА ИНВЕНТАРЯ ============
class InventoryRow(ButtonBehavior, BoxLayout):
    def __init__(self, item, inventory_screen, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        self.spacing = dp(8)
        self.padding = dp(6)
        self.item = item
        self.inventory_screen = inventory_screen
        
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
        info.add_widget(left_label(f"{item['price']:.0f} ₽ (Нажмите, чтобы продать)", font_size='11sp', color=(0.6, 0.6, 0.6, 1)))
        self.add_widget(info)
        
    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        
    def on_press(self):
        self.inventory_screen._sell_one(self.item)

# ==============================================================
# ЭКРАНЫ
# ==============================================================
class CaseListScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        
        # Добавили маленькую строчку статуса вверху, чтобы видеть, скачалась база или нет
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
            self.list_layout.add_widget(InventoryRow(it, self))

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

        # Оставили вашу высоту 800
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
                # Оставили вашу линию как было
                self.line.points = [cx, self.y +800, cx, self.y + 500]

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
        self.open_screen = OpeningScreen(app=self, name='opening')
        self.sm.add_widget(self.open_screen)
        root.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(2))
        btn_cases = Button(text='Кейсы', font_size='15sp', bold=True, background_color=(0.2, 0.4, 0.8, 1))
        btn_inv = Button(text='Инвентарь', font_size='15sp', bold=True, background_color=(0.2, 0.6, 0.3, 1))
        
        btn_cases.bind(on_press=lambda *a: setattr(self.sm, 'current', 'cases'))
        btn_inv.bind(on_press=lambda *a: setattr(self.sm, 'current', 'inventory'))
        
        nav.add_widget(btn_cases)
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
