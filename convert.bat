@echo off
pyuic6 -x .\ui\MainWindow.ui -o ./MainWindowUI.py
pyuic6 -x .\ui\InputDialog.ui -o ./InputDialogUI.py
pyside6-rcc resource.qrc -o resource_rc.py 