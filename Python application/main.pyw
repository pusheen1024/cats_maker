from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QDialog, QColorDialog, QFileDialog
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSize, QByteArray
from PyQt5.QtGui import QPixmap, QIcon
from PIL import Image, ImageDraw, ImageFilter
import sqlite3
from math import ceil
import random
import sys
import os
import registration
import mainwindow
import information
import gallery
import dialog_clear


DRAWING = 3
LINE = 2
FILL = 1
COLOR = 0
PROFIT = 10


def hex2rgb(string):
    first, second, third = string[1:3], string[3:5], string[5:7]
    return (int(first, 16), int(second, 16), int(third, 16))


def hash(string):
    res = 0
    for i in range(len(string)):
        res = (res + (ord(string[i]) ** i)) % 998244353
    return res


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


class Entry(registration.Ui_MainWindow, QMainWindow):
    def __init__(self):
        super().__init__()
        super().setupUi(self)
        self.database = Database()
        self.entry.clicked.connect(self.enter)
        self.registration.clicked.connect(self.register)

    def enter(self):
        login = self.login.text()
        password = hash(self.password.text())
        result = self.database.execute(f'SELECT password FROM passwords WHERE login="{login}"').fetchone()
        if result is not None:
            if result[0] == password:
                self.statusBar().showMessage('Вход в систему осуществлён успешно!')
                global mainwindow
                mainwindow = CatsMaker(login)
                mainwindow.show()
                self.close()
            else:
                self.statusBar().showMessage('Неправильный логин или пароль.')
        else:
            self.statusBar().showMessage('Пользователя с таким логином не существует.')

    def register(self):
        login = self.login1.text()
        password = hash(self.password1.text())
        password1 = hash(self.password1_repeat.text())
        if password == password1:
            if login and password:
                result = self.database.execute(f'SELECT password FROM passwords WHERE login="{login}"').fetchone()
                if result is not None:
                    self.statusBar().showMessage('Пользователь с таким логином уже есть в системе.')
                else:
                    self.database.execute(f'INSERT INTO passwords(login, password) VALUES("{login}", "{password}")')
                    self.database.execute(f'INSERT INTO profiles(login, rating) VALUES("{login}", 0)')
                    self.database.commit()
                    self.statusBar().showMessage('Регистрация успешно завершена!')
            else:
                self.statusBar().showMessage('Поля не должны быть пустыми.')
        else:
            self.statusBar().showMessage('Пароли не совпадают.')


class CatsMaker(mainwindow.Ui_MainWindow, QMainWindow):
    def __init__(self, login):
        super().__init__()
        super().setupUi(self)
        self.database = Database()
        self.login = login
        self.rating = self.database.execute(f'SELECT rating FROM profiles WHERE login="{login}"').fetchone()[0]
        self.initUi()
        self.stack = list()
        self.pictures = dict()
        self.storage = list()
        self.drawing_flag = False
        self.create_main()

    def initUi(self):
        self.profile_name.setText(self.login)
        for btn in self.accessories.buttons():
            btn.setIcon(QIcon(f'previews/accessories/{btn.objectName()}.png'))
            btn.setIconSize(QSize(45, 60))
            btn.clicked.connect(self.add_accessory)
        for btn in self.details.buttons():
            btn.setIcon(QIcon(f'previews/details/{btn.objectName()}.png'))
            btn.setIconSize(QSize(45, 60))
            btn.clicked.connect(self.add_detail)
        for btn in self.colors.buttons():
            btn.setIcon(QIcon(f'previews/colors/{btn.objectName()}.png'))
            btn.setIconSize(QSize(45, 60))
            btn.clicked.connect(self.add_color)
        for btn in self.filters.buttons():
            btn.setIcon(QIcon(f'previews/filters/{btn.objectName()}.png'))
            btn.setIconSize(QSize(45, 60))
            btn.clicked.connect(self.filter)
        self.main.setIcon(QIcon('previews/main.png'))
        self.main.setIconSize(QSize(45, 60))
        self.main.clicked.connect(self.change_main_color)
        pixmap = QPixmap('icons/profile_picture.png')
        pixmap_r = pixmap.scaled(40, 40, QtCore.Qt.KeepAspectRatio)
        self.profile_picture.resize(40, 40)
        self.profile_picture.setPixmap(pixmap_r)
        self.rating_widget.display(self.rating)
        self.save_button.setIcon(QIcon('icons/save_button.png'))
        self.save_button.setIconSize(QSize(40, 40))
        self.save_button.clicked.connect(self.save_picture)
        self.random_button.setIcon(QIcon('icons/random_button.png'))
        self.random_button.setIconSize(QSize(40, 40))
        self.random_button.clicked.connect(self.random_design)
        self.save_to_gallery_button.setIcon(QIcon('icons/save_to_gallery_button.png'))
        self.save_to_gallery_button.setIconSize(QSize(40, 40))
        self.save_to_gallery_button.clicked.connect(self.save_to_gallery)
        self.information.setIcon(QIcon('icons/information.png'))
        self.information.setIconSize(QSize(40, 40))
        self.information.clicked.connect(self.show_information)
        self.draw_button.setIcon(QIcon('icons/draw_button.png'))
        self.draw_button.setIconSize(QSize(40, 40))
        self.draw_button.clicked.connect(self.draw)
        self.clear_button.setIcon(QIcon('icons/clear_button.png'))
        self.clear_button.setIconSize(QSize(40, 40))
        self.clear_button.clicked.connect(self.clear)
        self.my_gallery.setIcon(QIcon('icons/my_gallery.png'))
        self.my_gallery.setIconSize(QSize(40, 40))
        self.my_gallery.clicked.connect(self.show_gallery)      
        self.progressBar.hide()

    def keyPressEvent(self, event):
        if int(event.modifiers()) == Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.save_picture()
            elif event.key() == Qt.Key_R:
                self.random_button.clicked.emit()
        elif int(event.modifiers()) == (Qt.ControlModifier + Qt.AltModifier):
            if event.key() == Qt.Key_C:
                self.clear()

    def mouseMoveEvent(self, event):
        if self.drawing_flag:
            size = 100
            x, y = event.x() * (size // 10) - size * 10, event.y() * (size // 10) - size * 5
            if self.prev[0] is not None:
                self.canvas.line((self.prev[0], self.prev[1], x, y), width=size, fill=self.color)
            else:
                self.canvas.ellipse((x, y, x + size, y + size), fill=self.color)
            name = 'drawing'
            if (DRAWING, name) in self.stack:
                self.stack.pop()
            self.stack.append((DRAWING, name))
            self.pictures[name] = self.drawing_picture
            self.merge_stack()
            self.prev = (x, y)

    def mouseReleaseEvent(self, event):
        self.prev = (None, None)

    def closeEvent(self, event):
        try:
            os.remove('tmp.png')
        except FileNotFoundError:
            pass

    def create_main(self, name='main', is_random=False):
        self.stack = list()
        self.current_picture = Image.open(f'{name}.png')
        self.x, self.y = self.current_picture.size
        self.stack.append((LINE, name))
        self.pictures[name] = self.current_picture
        self.merge_stack()

    def change_main_color(self, is_random=False):
        name = 'main'
        if not is_random:
            color = hex2rgb(QColorDialog.getColor().name())
        else:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.current_picture = Image.open(f'{name}_fill.png')
        pixels = self.current_picture.load()
        for i in range(self.x):
            for j in range(self.y):
                if pixels[i, j] != (255, 255, 255, 0):
                    pixels[i, j] = color
        self.stack.insert(0, (FILL, f'{name}_fill'))
        self.pictures[f'{name}_fill'] = self.current_picture
        self.merge_stack()

    def add_accessory(self, name=None, is_random=False):
        if not name:
            name = self.sender().objectName()
        self.current_picture = Image.open(f'accessories/line/{name}.png')
        if self.sender().count:
            for i in range(len(self.stack)):
                if self.stack[i][0] == DRAWING:
                    self.stack.insert(i, (LINE, name))
                    index = i
                    break
            else:
                self.stack.append((LINE, name))
                index = -1
            self.pictures[name] = self.current_picture
        else:
            self.stack.remove((LINE, name))
            del self.pictures[name]
        self.merge_stack()
        self.current_picture = Image.open(f'accessories/fill/{name}.png')
        if self.sender().count:
            if not is_random:
                color = hex2rgb(QColorDialog.getColor().name())
            else:
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            pixels = self.current_picture.load()
            for i in range(self.x):
                for j in range(self.y):
                    if pixels[i, j] != (255, 255, 255, 0):
                        pixels[i, j] = color
            self.stack.insert(index, (COLOR, f'{name}_fill'))
            self.pictures[f'{name}_fill'] = self.current_picture
        else:
            self.stack.remove((COLOR, f'{name}_fill'))
            del self.pictures[f'{name}_fill']
        self.merge_stack()

    def add_detail(self, name=None, is_random=False):
        if not name:
            name = self.sender().objectName()
        self.current_picture = Image.open(f'details/line/{name}.png')
        if name not in ('ears', 'nose'):
            if self.sender().count:
                for i in range(len(self.stack)):
                    if self.stack[i][0] == LINE:
                        self.stack.insert(i + 1, (LINE, name))
                        index = i + 1
                        self.pictures[name] = self.current_picture
                        break
            else:
                self.stack.remove((LINE, name))
                del self.pictures[name]
            self.merge_stack()
            self.current_picture = Image.open(f'details/fill/{name}.png')
            if self.sender().count:
                if not is_random:
                    color = hex2rgb(QColorDialog.getColor().name())
                else:
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                pixels = self.current_picture.load()
                for i in range(self.x):
                    for j in range(self.y):
                        if pixels[i, j] != (255, 255, 255, 0):
                            pixels[i, j] = color
                self.stack.insert(index, (COLOR, f'{name}_fill'))
                self.pictures[f'{name}_fill'] = self.current_picture
            else:
                self.stack.remove((COLOR, f'{name}_fill'))
                del self.pictures[f'{name}_fill']

        else:
            if self.sender().count:
                if not is_random:
                    color = hex2rgb(QColorDialog.getColor().name())
                else:
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                pixels = self.current_picture.load()
                for i in range(self.x):
                    for j in range(self.y):
                        if pixels[i, j] != (255, 255, 255, 0):
                            pixels[i, j] = color
                for i in range(len(self.stack)):
                    if self.stack[i][0] == LINE:
                        self.stack.insert(i, (COLOR, name))
                        self.pictures[name] = self.current_picture
                        break
            else:
                self.stack.remove((COLOR, name))
                del self.pictures[name]
        self.merge_stack()

    def add_color(self, name=None, is_random=False):
        if not name:
            name = self.sender().objectName()
        if self.sender().count:
            if not is_random:
                color = hex2rgb(QColorDialog.getColor().name())
            else:
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            self.current_picture = Image.open(f'colors/{name}.png')
            pixels = self.current_picture.load()
            for i in range(self.x):
                for j in range(self.y):
                    if pixels[i, j] != (255, 255, 255, 0):
                        pixels[i, j] = (*color, pixels[i, j][-1])
            for i in range(len(self.stack)):
                if self.stack[i][0] == LINE:
                    self.stack.insert(i, (COLOR, name))
                    self.pictures[name] = self.current_picture
                    break
        else:
            self.stack.remove((COLOR, name))
            del self.pictures[name]
        self.merge_stack()

    def merge_stack(self):
        blank = Image.new('RGBA', (self.x, self.y), (255, 255, 255, 0))
        for i in range(len(self.stack)):
            current_picture = self.pictures[self.stack[i][1]]
            blank.paste(current_picture, (0, 0), current_picture)
        blank.save('tmp.png')
        pixmap = QPixmap('tmp.png')
        pixmap_r = pixmap.scaled(225, 300, QtCore.Qt.KeepAspectRatio)
        self.picture.setPixmap(pixmap_r)

    def create_rainbow(self):
        rainbow = Image.new("RGB", (self.x, self.y), (0, 0, 0))
        canvas = ImageDraw.Draw(rainbow)
        n = ceil(self.y / 1024)
        for g in range(256):
            canvas.line((0, n * g, self.x, n * g), (255, g, 0), width=n)
        for r in range(256):
            canvas.line((0, n * (256 + r), self.x, n * (256 + r)), fill=(255 - r, 255, 0), width=n)
        for b in range(256):
            canvas.line((0, n * (512 + b), self.x, n * (512 + b)), fill=(0, 255, b), width=n)
        for g in range(256):
            canvas.line((0, n * (768 + g), self.x, n * (768 + g)), fill=(0, 255 - g, b), width=n)
        return rainbow

    @staticmethod
    def rainbow_check(func):
        def wrapper(self, *args):
            if not self.storage:
                rainbow_obj = self.create_rainbow()
                self.storage.append(rainbow_obj)
            return func(self, *args)
        return wrapper

    @rainbow_check
    def color_rainbow(self, pixels, i, j):
        pixels_1 = self.storage[0].load()
        r, g, b, _ = pixels[i, j]
        r_1, g_1, b_1 = pixels_1[i, j]
        r = int(0.6 * r + 0.4 * r_1)
        g = int(0.6 * g + 0.4 * g_1)
        b = int(0.6 * b + 0.4 * b_1)
        return r, g, b

    def filter(self):
        self.progressBar.show()
        self.progressBar.setValue(0)
        name = self.sender().objectName()
        self.current_picture = Image.open('tmp.png')
        if name == 'blur':
            self.current_picture = self.current_picture.filter(ImageFilter.GaussianBlur(radius=10))
            self.progressBar.setValue(100)
        else:
            pixels = self.current_picture.load()
            for i in range(self.x):
                self.progressBar.setValue(i // 30)
                for j in range(self.y):
                    if name == 'rainbow':
                        pixels[i, j] = self.color_rainbow(pixels, i, j)
                    else:
                        r, g, b, _ = pixels[i, j]
                        if name == 'sepia':
                            depth = 20
                            middle = (r + g + b) // 3
                            r = min(255, middle + depth * 2)
                            g = min(255, middle + depth)
                            b = min(255, middle)
                            pixels[i, j] = r, g, b
                        elif name == 'negate':
                            pixels[i, j] = 255 - r, 255 - g, 255 - b
                        elif name == 'black_and_white':
                            middle = (r + g + b) // 3
                            pixels[i, j] = middle, middle, middle
        self.current_picture.save('tmp.png')
        pixmap = QPixmap('tmp.png')
        pixmap_r = pixmap.scaled(225, 300, QtCore.Qt.KeepAspectRatio)
        self.picture.setPixmap(pixmap_r)
        self.progressBar.hide()

    def random_design(self):
        self.create_main()
        self.change_main_color(is_random=True)
        accessory = random.choice(self.accessories.buttons()).objectName()
        self.add_accessory(name=accessory, is_random=True)
        detail = random.choice(self.details.buttons()).objectName()
        self.add_detail(name=detail, is_random=True)
        for color in random.sample(self.colors.buttons(), 3):
            self.add_color(name=color.objectName(), is_random=True)
        self.sender().increment()

    def draw(self):
        if self.sender().count:
            self.drawing_flag = True
            self.drawing_picture = Image.new('RGBA', (self.x, self.y), (255, 255, 255, 0))
            self.canvas = ImageDraw.Draw(self.drawing_picture)
            self.color = hex2rgb(QColorDialog.getColor().name())
            self.prev = (None, None)

    def clear(self):
        dialog = DialogClear()
        if dialog.exec_():
            self.create_main()

    def save_picture(self):
        name = f'{QFileDialog.getSaveFileName()[0]}.png'
        final_picture = Image.open('tmp.png')
        final_picture.save(name)

    def save_to_gallery(self):
        picture1 = self.database.execute(f'SELECT picture1 FROM profiles WHERE login="{self.login}"').fetchone()
        picture1 = picture1[0] if picture1 is not None else None
        picture2 = self.database.execute(f'SELECT picture2 FROM profiles WHERE login="{self.login}"').fetchone()
        picture2 = picture2[0] if picture2 is not None else None
        picture3 = self.database.execute(f'SELECT picture3 FROM profiles WHERE login="{self.login}"').fetchone()
        picture3 = picture3[0] if picture3 is not None else None
        final_picture = sqlite3.Binary(open('tmp.png', 'rb').read())
        picture1, picture2, picture3 = final_picture, picture1, picture2
        try:
            self.database.execute(f'INSERT INTO profiles(login, picture1, picture2, picture3) VALUES(?, ?, ?, ?)', (self.login, picture1, picture2, picture3))
        except sqlite3.IntegrityError:
            self.database.execute(f'UPDATE profiles SET picture1 = ? WHERE login="{self.login}"', [picture1])
            self.database.execute(f'UPDATE profiles SET picture2 = ? WHERE login="{self.login}"', [picture2])
            self.database.execute(f'UPDATE profiles SET picture3 = ? WHERE login="{self.login}"', [picture3])
        self.rating += PROFIT
        self.database.execute(f'UPDATE profiles SET rating = (?) WHERE login="{self.login}"', [self.rating])
        self.rating_widget.display(self.rating)
        self.database.commit()

    def show_gallery(self):
        global gallery
        gallery = Gallery(self.login)
        gallery.show()

    def show_information(self):
        global information
        information = Information()
        information.show()


class DialogClear(dialog_clear.Ui_dialog, QDialog):
    def __init__(self):
        super().__init__()
        super().setupUi(self)


class Gallery(gallery.Ui_Form, QWidget):
    def __init__(self, login):
        super().__init__()
        super().setupUi(self)
        self.database = Database()
        picture1 = self.database.execute(f'SELECT picture1 FROM profiles WHERE login="{login}"').fetchone()[0]
        if picture1 is not None:
            image = QByteArray(picture1)
            pixmap = QPixmap()
            pixmap.loadFromData(image, 'PNG')
            pixmap_r = pixmap.scaled(225, 300, QtCore.Qt.KeepAspectRatio)
            self.p1.setPixmap(pixmap_r)
        picture2 = self.database.execute(f'SELECT picture2 FROM profiles WHERE login="{login}"').fetchone()[0]
        if picture2 is not None:
            image = QByteArray(picture2)
            pixmap = QPixmap()
            pixmap.loadFromData(image, 'PNG')
            pixmap_r = pixmap.scaled(225, 300, QtCore.Qt.KeepAspectRatio)
            self.p2.setPixmap(pixmap_r)
        picture3 = self.database.execute(f'SELECT picture3 FROM profiles WHERE login="{login}"').fetchone()[0]
        if picture3 is not None:
            image = QByteArray(picture3)
            pixmap = QPixmap()
            pixmap.loadFromData(image, 'PNG')
            pixmap_r = pixmap.scaled(225, 300, QtCore.Qt.KeepAspectRatio)
            self.p3.setPixmap(pixmap_r)


class Information(information.Ui_Dialog, QDialog):
    def __init__(self):
        super().__init__()
        super().setupUi(self)


class Database:
    def __init__(self):
        self.con = sqlite3.connect('database')
        self.cur = self.con.cursor()

    def execute(self, *args):
        return self.cur.execute(*args)

    def commit(self, *args):
        self.con.commit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Entry()
    window.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
