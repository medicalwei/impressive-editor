#!/usr/bin/env python
# -*- coding: utf-8 -*-

import impressiveEditorUI
from PyQt4 import QtCore, QtGui
import tempfile
import subprocess
import shutil
import sys
import os
import copy
import re
from multiprocessing import Process

execfile(os.path.dirname(os.path.realpath(sys.argv[0]))+"/infoscript-tools.py")

class ThumbnailLoader(QtCore.QThread):
    def run(self):
        subprocess.call(['convert', "%s" % (impressiveEditor.FilePath), '-density', '600', '-resize', '100x100', "%s/p.png" % (impressiveEditor.ImageDirectory)])

class MainWindow(QtGui.QMainWindow):
    def closeEvent(self, event):
        impressiveEditor.saveCheck(event.accept, event.ignore)

class HistoryRecorder():
    def __init__(self, current):
        self.undoList = []
        self.redoList = []
        self.current = copy.deepcopy(current)

    def do(self, data):
        self.undoList.append(self.current)
        self.current = copy.deepcopy(data)
        if self.redoCount() > 0:
            self.redoList = []

    def undo(self):
        data = self.undoList.pop()
        self.redoList.append(self.current)
        self.current = data
        return data

    def redo(self):
        data = self.redoList.pop()
        self.undoList.append(self.current)
        self.current = data
        return data

    def undoCount(self):
        return len(self.undoList)

    def redoCount(self):
        return len(self.redoList)

class ImpressiveEditor:
    def __init__(self):
        self.ImageDirectory = ""
        self.currentSelected = -1
        self.notSaved = False

        self.MainWindow = MainWindow()
        self.UI = impressiveEditorUI.Ui_MainWindow()

        self.UI.setupUi(self.MainWindow)

        self.thumbnailLoader = ThumbnailLoader()
        self.loadingIcon = QtGui.QIcon(os.path.dirname(os.path.realpath(sys.argv[0]))+"/loading.png")

        # set up transitions
        self.UI.transition.addItem(self.tr("Not Specified"), None)
        for transition in AllTransitions:
            self.UI.transition.addItem(transition.__name__, transition)

        self.UI.actionOpen.triggered.connect(self.actionOpen)
        self.UI.actionOpenInfo.triggered.connect(self.actionOpenInfo)
        self.UI.actionSave.triggered.connect(self.actionSave)
        self.UI.actionSaveAs.triggered.connect(self.actionSaveAs)
        self.UI.actionQuit.triggered.connect(self.actionQuit)
        self.UI.actionCopy.triggered.connect(self.copy)
        self.UI.actionPaste.triggered.connect(self.paste)
        self.UI.actionPasteAll.triggered.connect(self.pasteAll)
        self.UI.actionStart.triggered.connect(self.startPresentation)
        self.UI.actionUndo.triggered.connect(self.undo)
        self.UI.actionRedo.triggered.connect(self.redo)
        self.thumbnailLoader.finished.connect(self.reloadThumbnail)

    def start(self):
        self.MainWindow.show()
        self.actionOpen()

    def connectConfigs(self):
        self.UI.skipThisSlide.stateChanged.connect(self.skipThisSlideChanged)
        self.UI.transition.currentIndexChanged.connect(self.transitionChanged)
        self.UI.transitionTime.valueChanged.connect(self.transitionTimeChanged)

    def disconnectConfigs(self):
        try:
            self.UI.skipThisSlide.stateChanged.disconnect()
            self.UI.transition.currentIndexChanged.disconnect()
            self.UI.transitionTime.valueChanged.disconnect()
        except:
            pass

    def loadSlide(self):
        try:
            self.UI.slides.currentItemChanged.disconnect()
        except:
            pass
        self.cleanTemp()
        self.UI.slides.clear()
        self.thumbnailLoader.terminate()
        self.ImageDirectory = tempfile.mkdtemp()
        self.MainWindow.setWindowTitle(self.FilePath)

        pdfinfo = subprocess.Popen(['pdfinfo', self.FilePath], stdout=subprocess.PIPE).communicate()[0]
        self.count = int(re.search('Pages: +(\d+)', pdfinfo).groups()[0])
        (realWidth, realHeight) = map(float, re.search('Page size: +([0-9.]+) x ([0-9.]+)', pdfinfo).groups())
        if realWidth > realHeight:
            (thumbnailWidth, thumbnailHeight) = (100, 100*realHeight/realWidth)
        else:
            (thumbnailWidth, thumbnailHeight) = (100*realWidth/realHeight, 100)
        thumbnailQSize = QtCore.QSize(thumbnailWidth, thumbnailHeight)

        self.UI.slides.currentItemChanged.connect(self.currentSlideChanged)

        for i in range(self.count) :
            item = QtGui.QListWidgetItem()
            # FIXME: workaround used here
            # http://stackoverflow.com/questions/9257422/how-to-get-the-original-python-data-from-qvariant
            item.setData(QtCore.Qt.UserRole, ({"id": i+1},))
            item.setIcon(self.loadingIcon)
            self.updateStatus(item)
            self.UI.slides.addItem(item)
            if i == 0:
                self.UI.slides.setCurrentItem(item)

        self.UI.slides.setIconSize(thumbnailQSize)

        self.thumbnailLoader.start()

    def reloadThumbnail(self):
        for i in range(self.count):
            item = self.UI.slides.item(i)
            icon = QtGui.QIcon("%s/p-%d.png" % (self.ImageDirectory, i))
            item.setIcon(icon)

    def loadProp(self, propPath):
        global InfoScriptPath
        InfoScriptPath = propPath
        LoadInfoScript()
        self.notSaved = False
        self.historyRecorder = HistoryRecorder(PageProps)

    def actionSave(self):
        SaveInfoScript(InfoScriptPath)
        self.notSaved = False
        return True

    def actionSaveAs(self):
        f = QtGui.QFileDialog.getSaveFileName(self.MainWindow, self.tr("Save Info Script"), "", "Info Script (*info)")
        if not f:
            return False
        SaveInfoScript(str(f))
        self.notSaved = False
        return True

    def cleanTemp(self):
        if self.ImageDirectory != "":
            shutil.rmtree(self.ImageDirectory)

    def actionOpen(self):
        impressiveEditor.saveCheck(self.actionOpenCall)

    def actionOpenCall(self):
        f = QtGui.QFileDialog.getOpenFileName(self.MainWindow, self.tr("Open Slide"), "", "PDF (*.pdf)")
        if not f:
            return False

        self.FilePath = str(f)
        propPath = self.FilePath + ".info"

        self.loadProp(propPath)
        self.loadSlide()

        self.UI.actionOpenInfo.setEnabled(True)
        self.UI.actionSave.setEnabled(True)
        self.UI.actionSaveAs.setEnabled(True)
        self.UI.actionCopy.setEnabled(True)

        return True

    def actionOpenInfo(self):
        impressiveEditor.saveCheck(self.actionOpenInfoCall)

    def actionOpenInfoCall(self):
        f = QtGui.QFileDialog.getOpenFileName(self.MainWindow, self.tr("Open Info Script"), "", "Info Script (*.info)")
        if not f:
            return

        propPath = str(f)
        self.loadProp(propPath)

    def actionQuit(self):
        self.MainWindow.close()

    def currentSlideChanged(self, currentItem):
        self.disconnectConfigs()
        data = currentItem.data(QtCore.Qt.UserRole).toPyObject()[0]
        self.currentSelected = data["id"]
        self.currentSelectedWidget = currentItem
        self.updateStatus()
        self.updateUI()
        self.connectConfigs()

    def updateUI(self):
        self.UI.skipThisSlide.setChecked(GetPageProp(self.currentSelected, "skip", False))

        transitionComboBoxId = 0
        currentTransition = GetPageProp(self.currentSelected, "transition")
        if currentTransition:
            transitionComboBoxId = self.UI.transition.findText(currentTransition.__name__)
        self.UI.transition.setCurrentIndex(transitionComboBoxId)

        self.UI.transitionTime.setValue(GetPageProp(self.currentSelected, "transtime", 0)/1000.0)

    def updateStatus(self, widget = False):
        if not widget:
            widget = self.currentSelectedWidget
        i = widget.data(QtCore.Qt.UserRole).toPyObject()[0]["id"]

        desc = "%s %d" % (self.tr("Slide"), i)

        if GetPageProp(i, "skip", False):
            desc += "\n - %s" % (self.tr("Skipped"))

        transition = GetPageProp(i, "transition")
        if transition:
            desc += "\n - %s: %s" % (self.tr("T"), transition.__name__)

        transitionTime = GetPageProp(i, "transtime")
        if transitionTime:
            desc += u"\n - %s: %.2f" % (self.tr("T@"), (transitionTime/1000.0))

        widget.setText(desc)

    def postChanged(self, forAll=False, noHistory=False):
        if not noHistory:
            self.historyRecorder.do(PageProps)
            self.UI.actionUndo.setEnabled(self.historyRecorder.undoCount())
            self.UI.actionRedo.setEnabled(self.historyRecorder.redoCount())
        self.notSaved = True
        if forAll:
            for i in range(self.count):
                self.updateStatus(self.UI.slides.item(i))
        else:
            self.updateStatus()

    def skipThisSlideChanged(self, state):
        if state == 2:
            SetPageProp(self.currentSelected, "skip", True)
        elif GetPageProp(self.currentSelected, "skip"):
            PageProps[self.currentSelected].pop("skip")
        self.postChanged()

    def transitionChanged(self, item):
        transition = self.UI.transition.itemData(item).toPyObject()
        if transition:
            SetPageProp(self.currentSelected, "transition", transition)
        elif GetPageProp(self.currentSelected, "transition"):
            PageProps[self.currentSelected].pop("transition")
        self.postChanged()

    def transitionTimeChanged(self, value):
        if value > 0:
            SetPageProp(self.currentSelected, "transtime", int(value*1000))
        elif GetPageProp(self.currentSelected, "transtime"):
            PageProps[self.currentSelected].pop("transtime")
        self.postChanged()

    def copy(self):
        self.clipboard = copy.deepcopy(PageProps[self.currentSelected])
        self.UI.actionPaste.setEnabled(True)
        self.UI.actionPasteAll.setEnabled(True)

    def paste(self):
        self.disconnectConfigs()
        PageProps[self.currentSelected] = copy.deepcopy(self.clipboard)
        self.updateUI()
        self.postChanged()
        self.connectConfigs()

    def pasteAll(self):
        self.disconnectConfigs()
        for i in range(self.count):
            PageProps[i+1] = copy.deepcopy(self.clipboard)
        self.updateUI()
        self.postChanged(True)
        self.connectConfigs()

    def startPresentation(self):
        self.saveCheck(self.startPresentationCall, None, self.tr("Do you want to save your changes before start presentation?"))

    def startPresentationCall(self):
        # TODO: need impressive path
        try:
            subprocess.call(['impressive', '--script', InfoScriptPath, self.FilePath])
        except OSError:
            ret = QtGui.QMessageBox.critical(
                    self.MainWindow,
                    self.tr("Presentation cannot be started."),
                    self.tr("Presentation cannot be started.\nMake sure you have Impressive installed in your computer."),
                    QtGui.QMessageBox.Ok
                    )

    def saveCheck(self, accept, cancel=None, message=None):
        if not message:
            message = self.tr("Do you want to save your changes?")

        if self.notSaved:
            ret = QtGui.QMessageBox.information(
                    self.MainWindow,
                    self.tr("The script has been modified."),
                    message,
                    QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel,
                    QtGui.QMessageBox.Save
                    )

            if ret == QtGui.QMessageBox.Cancel:
                if cancel:
                    cancel()
            elif ret == QtGui.QMessageBox.Save:
                if impressiveEditor.actionSave():
                    accept()
                elif cancel:
                    cancel()
            elif ret == QtGui.QMessageBox.Discard:
                accept()
        else:
            accept()

    def postHistory(self):
        self.disconnectConfigs()
        self.UI.actionUndo.setEnabled(self.historyRecorder.undoCount())
        self.UI.actionRedo.setEnabled(self.historyRecorder.redoCount())
        self.updateUI()
        self.postChanged(True, True)
        self.connectConfigs()

    def undo(self):
        global PageProps
        PageProps = self.historyRecorder.undo()
        self.postHistory()

    def redo(self):
        global PageProps
        PageProps = self.historyRecorder.redo()
        self.postHistory()

    def tr(self, s):
        return QtCore.QCoreApplication.translate("ImpressiveEditor", s)

if __name__ == "__main__":
    import sys
    global impressiveEditor
    app = QtGui.QApplication(sys.argv)

    locale = QtCore.QLocale.system().name()
    qtTranslator = QtCore.QTranslator()
    if qtTranslator.load("qt_"+locale):
        app.installTranslator(qtTranslator)
    appTranslator = QtCore.QTranslator()
    if appTranslator.load("impressive-editor_"+locale, os.path.dirname(os.path.realpath(sys.argv[0]))+"/locales"):
        app.installTranslator(appTranslator)

    impressiveEditor = ImpressiveEditor()
    impressiveEditor.start()
    ret = app.exec_()
    impressiveEditor.thumbnailLoader.terminate()
    impressiveEditor.cleanTemp()
    sys.exit(ret)
