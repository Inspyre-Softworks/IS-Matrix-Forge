import PySimpleGUI as sg


MENU_DEF = [
    ['File', [
        'Export',
        'Export to File',
        'Load from File',
        '---',
        'Exit'
    ]],
    ['Matrix', [
        'Send to Matrix'
    ]],
    ['Frame', [
        'Add Frame'
    ]]
]


class MenuBar:
    def __init__(self):
        self.__layout   = None
        self.__menu_bar = None

    @property
    def is_built(self):
        return self.__layout is not None and self.__menu_bar is not None

    @property
    def layout(self):
        return self.__layout

    @property
    def menu_bar(self):
        return self.__menu_bar

    def build(self):
        if self.__layout is not None and self.menu_bar is not None:




