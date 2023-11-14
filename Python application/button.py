from PyQt5.QtWidgets import QPushButton


class Button(QPushButton):
    def __init__(self, *args):
        super().__init__(*args)
        self.count = 0
        self.clicked.connect(self.increment)

    def increment(self):
        self.count ^= 1

