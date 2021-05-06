#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import hashlib
from inspect import signature
import json
import ctypes

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt

import coders


CONFIG_FILE = 'config.json'


class MainWindow(QMainWindow):
    """main window defines here"""
    def __init__(self):
        """init ui and connect some callbacks"""
        super().__init__()
        uic.loadUi('main.ui', self)
        self.hide_error()
        self.load_params()

        self.convert_button.clicked.connect(self.convert)
        self.radio_encode.toggled.connect(self.switch_mode_callback)
        self.radio_decode.toggled.connect(self.switch_mode_callback)
        self.radio_hash.toggled.connect(self.switch_mode_callback)
        self.coding_selector.currentTextChanged\
            .connect(self.switch_algorithm_callback)

        self.coders_list = coders.CODERS
        self.decoders_list = coders.DECODERS
        hash_algs = hashlib.algorithms_available
        self.hashes_list = [str(hs) for hs in sorted(hash_algs)]

        self.save_filename = ''

        self.about_dialog = AboutWindow()
        self.menu_about.triggered.connect(self.about_dialog.show)

        self.help_dialog = HelpWindow()
        self.menu_help.setShortcuts(QKeySequence('Ctrl+H'))
        self.menu_help.triggered.connect(self.help_dialog.show)

        self.actionOpen.setShortcuts(QKeySequence('Ctrl+O'))
        self.actionOpen.triggered.connect(self.open_file)
        self.actionSave.setShortcuts(QKeySequence('Ctrl+S'))
        self.actionSave.triggered.connect(self.save_file)
        self.actionSave_As.setShortcuts(QKeySequence('Ctrl+Shift+S'))
        self.actionSave_As.triggered.connect(lambda e: self.save_file(True))
        self.actionExit.setShortcuts((QKeySequence('Ctrl+Q'),
                                      QKeySequence('Escape')))
        self.actionExit.triggered.connect(self.close)

        self.actionCut.setShortcuts(QKeySequence('Ctrl+X'))
        self.actionCut.triggered.connect(self.text_field.cut)
        self.actionCopy.setShortcuts(QKeySequence('Ctrl+C'))
        self.actionCopy.triggered.connect(self.text_field.copy)
        self.actionPaste.setShortcuts(QKeySequence('Ctrl+V'))
        self.actionPaste.triggered.connect(self.text_field.paste)
        self.actionClear.setShortcuts(QKeySequence('Ctrl+Backspace'))
        self.actionClear.triggered.connect(self.text_field.clear)

        for file_name in self.params['recent_files']:
            recentAction = QAction(file_name, self)
            # recentAction.setShortcut("Ctrl+A")
            # recentAction.setStatusTip('Leave The App')
            recentAction.triggered.connect(self.close)
            self.menuOpen_recent.insertAction(self.actionClear_items, recentAction)

        if os.name == 'nt':
            # some Шindows black magic here
            # setting taskbar icon
            myappid = 'mycompany.myproduct.subproduct.version'
            ctypes.windll.shell32\
                .SetCurrentProcessExplicitAppUserModelID(myappid)

        if 'last_mode' not in self.params or \
           self.params['last_mode'] == 'encode':
            self.radio_encode.setChecked(True)
        elif self.params['last_mode'] == 'decode':
            self.radio_decode.setChecked(True)
        else:
            self.radio_hash.setChecked(True)

    def open_file(self):
        dir_path = os.path.abspath(os.getcwd())
        if 'save_dir' in self.params:
            dir_path = self.params['save_dir']
        file_name = QFileDialog.getOpenFileName(self,
                                                'Open file',
                                                dir_path)[0]
        if file_name:
            self.save_filename = file_name
            self.params['save_dir'] = os.path.dirname(
                os.path.abspath(self.save_filename))
            try:
                text = open(self.save_filename, 'r').read()
                self.text_field.setPlainText(text)
            except Exception as ex:
                self.show_error(ex.__class__.__name__, str(ex))

    def save_file(self, newfile=False):
        file_name = ''
        dir_path = os.path.abspath(os.getcwd())
        if 'save_dir' in self.params:
            dir_path = self.params['save_dir']
        if not self.save_filename or newfile:
            file_name = QFileDialog.getSaveFileName(self,
                                                    'Save file',
                                                    dir_path)[0]
        if file_name:
            self.save_filename = file_name
        if newfile and not file_name:
            return
        self.params['save_dir'] = os.path.dirname(
            os.path.abspath(self.save_filename))
        text = self.text_field.toPlainText()
        try:
            open(self.save_filename, 'w').write(text)
        except Exception as ex:
            self.show_error(ex.__class__.__name__, str(ex))

    def closeEvent(self, event):
        """close child forms and save self form dimensions and some params"""
        self.about_dialog.close()
        self.help_dialog.close()
        self.save_params()

    def save_params(self):
        """serialize params dict and write to pretty .json file"""
        self.params['maximazed'] = self.isMaximized()
        if not self.params['maximazed']:
            self.params['geometry'] = self.geometry().getRect()

        with open(CONFIG_FILE, 'w') as fp:
            json.dump(self.params, fp, sort_keys=True, indent=4)

    def load_params(self):
        """trying to read params from .json file and
        set main window params if available"""
        try:
            with open(CONFIG_FILE, 'r') as fp:
                self.params = json.load(fp)
        except FileNotFoundError:
            self.params = dict()
        if 'recent_files' not in self.params:
            self.params['recent_files'] = dict()
        if 'geometry' in self.params:
            self.setGeometry(*self.params['geometry'])
        if 'maximazed' in self.params and self.params['maximazed']:
            self.showMaximized()

    def switch_mode_callback(self, event):
        """process clicks on radiobuttons"""
        if self.radio_encode.isChecked():
            self.set_drop_down_coders()
            self.params['last_mode'] = 'encode'
        elif self.radio_decode.isChecked():
            self.set_drop_down_decoders()
            self.params['last_mode'] = 'decode'
        elif self.radio_hash.isChecked():
            self.set_drop_down_hashes()
            self.params['last_mode'] = 'hash'

    def switch_algorithm_callback(self, event):
        """process drop-down menu select"""
        self.hile_key_spin()
        self.hile_key_field()

        if self.radio_encode.isChecked() and event in self.coders_list:
            self.params['last_coder'] = event
            if coders.is_key(event) == coders.KEY_DECIMAL:
                self.show_key_spin()
            elif coders.is_key(event) == coders.KEY_TEXT:
                self.show_key_field()

        elif self.radio_decode.isChecked() and event in self.decoders_list:
            self.params['last_decoder'] = event
            if coders.is_key(event) == coders.KEY_DECIMAL:
                self.show_key_spin()
            elif coders.is_key(event) == coders.KEY_TEXT:
                self.show_key_field()

        elif event in self.hashes_list:
            self.params['last_hash'] = event

    def get_md(self, string, algorithm):
        """calc digest and show to user"""
        hash_obj = hashlib.new(algorithm, string.encode('utf-8'))
        try:
            sig = signature(hash_obj.hexdigest).parameters
        except ValueError:
            sig = ()
        if len(sig) == 0:
            return hash_obj.hexdigest()
        else:
            return hash_obj.hexdigest(1024)

    def encode(self, string, algorithm, key=None):
        """process text encoding"""
        error, text = coders.encode(string, algorithm, key)
        if error:
            self.show_error(error['title'], error['text'])
        return text

    def decode(self, string, algorithm, key=None):
        """process text decoding"""
        error, text = coders.decode(string, algorithm, key)
        if error:
            self.show_error(error['title'], error['text'])
        return text

    def convert(self):
        """convert button callback, select method and process text"""
        self.hide_error()
        key_type = coders.is_key(self.coding_selector.currentText())
        key = None
        if key_type == coders.KEY_DECIMAL:
            key = self.key_spin.value()
        elif key_type == coders.KEY_TEXT:
            key = self.key_field.text()

        if self.radio_encode.isChecked():
            text = self.encode(self.text_field.toPlainText(),
                               self.coding_selector.currentText(),
                               key)

        elif self.radio_decode.isChecked():
            text = self.decode(self.text_field.toPlainText(),
                               self.coding_selector.currentText(),
                               key)

        elif self.radio_hash.isChecked():
            text = self.get_md(self.text_field.toPlainText(),
                               self.coding_selector.currentText())

        else:
            raise ZeroDivisionError('Oh shi~')

        self.text_field.setPlainText(text)

    def show_key_spin(self):
        """show numeric key field"""
        self.hile_key_field()
        self.key_label.show()
        self.key_spin.show()

    def hile_key_spin(self):
        """hide numeric key field"""
        self.key_label.hide()
        self.key_spin.hide()

    def show_key_field(self):
        """show text key field"""
        self.hile_key_spin()
        self.key_label.show()
        self.key_field.show()

    def hile_key_field(self):
        """hide text key field"""
        self.key_label.hide()
        self.key_field.hide()

    def set_drop_down_coders(self):
        """fill drop-down menu with coders methods"""
        index = 0
        if 'last_coder' in self.params:
            index = self.coders_list.index(self.params['last_coder'])
        self.coding_selector.clear()
        self.coding_selector.addItems(self.coders_list)
        self.coding_selector.setCurrentIndex(index)

    def set_drop_down_decoders(self):
        """fill drop-down menu with decoders methods"""
        index = 0
        if 'last_decoder' in self.params:
            index = self.decoders_list.index(self.params['last_decoder'])
        self.coding_selector.clear()
        self.coding_selector.addItems(self.decoders_list)
        self.coding_selector.setCurrentIndex(index)

    def set_drop_down_hashes(self):
        """fill drop-down menu with hash algorithms"""
        index = 0
        if 'last_hash' in self.params:
            index = self.hashes_list.index(self.params['last_hash'])
        self.coding_selector.clear()
        self.coding_selector.addItems(self.hashes_list)
        self.coding_selector.setCurrentIndex(index)

    def hide_error(self):
        """hide error field"""
        self.error_label.hide()

    def show_error(self, error_title, error_text):
        """show error field with some data about error"""
        self.error_label.setText(error_title)
        self.error_label.setToolTip(error_text)
        self.error_label.setStyleSheet("color: red")
        self.error_label.show()


class AboutWindow(QDialog):
    """About dialog with some text, image and close button"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        uic.loadUi('about.ui', self)
        self.setFixedSize(self.size())
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.close_button.clicked.connect(self.close)
        self.about_field.setText('Yet another PyQT5 demo application '
                                 'made on Earth\nby humans?')
        self.author_label.setText('89dd33736a5f5ff75891479a4e633897')


class HelpWindow(QDialog):
    """Help dialog with rendered README.md on text-browser field"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        uic.loadUi('help.ui', self)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.close_button.clicked.connect(self.close)

        readme = open('README.md', 'r').read()
        # self.help_field.setMarkdown(readme)
        self.help_field.setText('I need somebody!\n'
                                '\tHelp!\n'
                                'Not just anybody\n'
                                '\tHelp!\n'
                                'You know I need someone\n'
                                '\tHeeelp~\n\n' + readme)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
