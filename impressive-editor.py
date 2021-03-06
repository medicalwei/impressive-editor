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
import math
import argparse

execfile(os.path.dirname(os.path.realpath(sys.argv[0]))+"/infoscript-tools.py")

class ThumbnailLoader(QtCore.QThread):
    def run(self):
        subprocess.call(["pdftocairo", "-png", "-scale-to", "100", impressiveEditor.FilePath, "%s/p" % (impressiveEditor.ImageDirectory)])

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
    def __init__(self, args):
        self.ImageDirectory = ""
        self.currentSelected = -1
        self.notSaved = False
        self.args = args

        self.MainWindow = MainWindow()
        self.UI = impressiveEditorUI.Ui_MainWindow()

        self.UI.setupUi(self.MainWindow)

        self.thumbnailLoader = ThumbnailLoader()
        self.loadingIcon = QtGui.QIcon(os.path.dirname(os.path.realpath(sys.argv[0]))+"/data/loading.svg")
        self.windowIcon = QtGui.QIcon(os.path.dirname(os.path.realpath(sys.argv[0]))+"/data/impressive-editor.svg")
        self.MainWindow.setWindowIcon(self.windowIcon)

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
        self.UI.actionAbout.triggered.connect(self.about)
        self.UI.actionStarterGuide.triggered.connect(self.guide)
        self.thumbnailLoader.finished.connect(self.reloadThumbnail)

    def start(self):
        self.MainWindow.show()

        if self.args.filepath:
            if self.args.infopath:
                self.loadProp(self.args.infopath)
            else:
                self.loadProp(self.args.filepath+".info")

            self.loadSlide(self.args.filepath)

            if self.args.start:
                self.startPresentation()
        else:
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

    def loadSlide(self, filePath):
        try:
            self.UI.slides.currentItemChanged.disconnect()
        except:
            pass

        info = subprocess.Popen(['file', filePath], stdout=subprocess.PIPE).communicate()[0]
        if info.find("PDF document") == -1:
            QtGui.QMessageBox.critical(
                self.MainWindow,
                self.tr("This file cannot be opened."),
                self.tr("Impressive Editor cannot open this file for presentation."),
                QtGui.QMessageBox.Ok
                )
            return

        self.FilePath = filePath
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

        self.UI.actionOpenInfo.setEnabled(True)
        self.UI.actionSave.setEnabled(True)
        self.UI.actionSaveAs.setEnabled(True)
        self.UI.actionCopy.setEnabled(True)

    def reloadThumbnail(self):
        zfillRate = int(math.log10(self.count+1))+1
        for i in range(self.count):
            item = self.UI.slides.item(i)
            name = str(i+1).zfill(zfillRate)
            icon = QtGui.QIcon("%s/p-%s.png" % (self.ImageDirectory, name))
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
        f = QtGui.QFileDialog.getSaveFileName(self.MainWindow, self.tr("Save Info Script"), "", self.tr("Info Script (*.info)"))
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
        f = QtGui.QFileDialog.getOpenFileName(self.MainWindow, self.tr("Open PDF Slide"), "", self.tr("PDF (*.pdf)"))
        if not f:
            return False

        filePath = str(f.toUtf8())
        propPath = filePath + ".info"
        self.loadProp(propPath)
        self.loadSlide(filePath)

        return True

    def actionOpenInfo(self):
        impressiveEditor.saveCheck(self.actionOpenInfoCall)

    def actionOpenInfoCall(self):
        f = QtGui.QFileDialog.getOpenFileName(self.MainWindow, self.tr("Open Info Script"), "", self.tr("Info Script (*.info)"))
        if not f:
            return

        self.loadProp(str(f))

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
        # showing guide
        if not settings.value("skipGuide").toBool():
            self.guide(True)

        # TODO: need impressive path
        try:
            subprocess.call(['impressive', '--script', InfoScriptPath, self.FilePath])
        except OSError:
            QtGui.QMessageBox.critical(
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

    def about(self, s):
        QtGui.QMessageBox.about(self.MainWindow, self.tr("About"),
                self.tr('''<h1>Impressive Editor</h1>
<p>Editor for Impressive presentation tool</p>
<p>Yao Wei &lt;<a href="mailto:mwei@lxde.org">mwei@lxde.org</a>&gt;</p>
<p><a href="https://github.com/medicalwei/impressive-editor">Fork me or report issues on GitHub</a></p>
<p>Licensed under GNU GPL v2<br>
(see COPYING or distro-specific locations for details)</p>
'''))

    def guide(self, init):
        title = self.tr("Starter Guide")
        message = self.tr('''
<p>Impressive itself is a simple presentation tool which makes PDF vivid.</p>
<h2>Basics</h2>
<b>F5</b> &mdash; Start Presentation<br>
<b>Page Down</b>, <b>Space Bar</b> &mdash; Next Slide<br>
<b>Page Up</b>, <b>Backspace</b> &mdash; Previous Slide<br>
<b>Tab</b> &mdash; Show Overview<br>
<b>Q</b>, <b>Esc</b> &mdash; Exit Presentation
<h2>Focus and Spotlight</h2>
Drag Rectangle with <b>Left Mouse Button</b> &mdash; Focus<br>
<b>Right Mouse Button</b> on Rectangle &mdash; Remove Focus<br>
<b>Enter</b> &mdash; Spotlight<br>
<b>+</b>, <b>-</b> &mdash; Spotlight Zoom
<h2>Zooming</h2>
<b>Z</b> &mdash; Toggle Zooming<br>
Dragging with <b>Right Mouse Button</b> when Zooming &mdash; Panning
''')
        messageBox = QtGui.QMessageBox(QtGui.QMessageBox.NoIcon, title, message, QtGui.QMessageBox.Ok, self.MainWindow)
        if init:
            never = messageBox.addButton(self.tr("Don't show this message again"), QtGui.QMessageBox.NoRole)
            messageBox.exec_()
            if messageBox.clickedButton() == never:
                settings.setValue("skipGuide", True)
        else:
            messageBox.exec_()

    def tr(self, s):
        return QtCore.QCoreApplication.translate("ImpressiveEditor", s)

if __name__ == "__main__":
    global impressiveEditor
    
    parser = argparse.ArgumentParser(description='Display and Edit effects on PDF slides. Front-end of Impressive presentation tool.')
    parser.add_argument('filepath', metavar='pdfpath', type=str, nargs='?', help='path to your PDF slides')
    parser.add_argument('-i', '--infopath', metavar='infopath', dest='infopath', type=str, nargs=1, help='path to your info script for the slides')
    parser.add_argument('-s', '--start', dest='start', action='store_true', help='start presentation immediately')
    args = parser.parse_args()

    QtCore.QTextCodec.setCodecForCStrings(QtCore.QTextCodec.codecForName("UTF-8"))
    app = QtGui.QApplication(sys.argv)

    global settings
    settings = QtCore.QSettings("impressive-editor")

    locale = QtCore.QLocale.system().name()
    qtTranslator = QtCore.QTranslator()
    if qtTranslator.load("qt_"+locale):
        app.installTranslator(qtTranslator)
    appTranslator = QtCore.QTranslator()
    qtTranslator = QtCore.QTranslator()
    if appTranslator.load("impressive-editor_"+locale, os.path.dirname(os.path.realpath(sys.argv[0]))+"/locales"):
        app.installTranslator(appTranslator)
    if qtTranslator.load("qt_"+locale, QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)):
        app.installTranslator(qtTranslator)

    impressiveEditor = ImpressiveEditor(args)
    impressiveEditor.start()
    ret = app.exec_()
    impressiveEditor.thumbnailLoader.terminate()
    impressiveEditor.cleanTemp()
    sys.exit(ret)
