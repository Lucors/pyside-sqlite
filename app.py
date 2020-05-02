# -*- coding: utf-8 -*-

from PySide import QtCore, QtGui, QtSql
import sys

global sqlDB


class AutoIncrement(QtGui.QItemDelegate):
    def __init__(self, parent=None):
        super(AutoIncrement, self).__init__(parent)

    def createEditor(self, parent, option, index): pass
    def setEditorData(self, editor, index): pass
    def setModelData(self, editor, model, index):pass


class BoolDelegate(QtGui.QItemDelegate):
    def __init__(self, parent=None):
        super(BoolDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        self.drawCheck(painter, option, option.rect, QtCore.Qt.Checked if index.data() == 'TRUE' else QtCore.Qt.Unchecked)
        self.drawFocus(painter, option, option.rect)

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            return model.setData(index, 'FALSE' if index.data() == 'TRUE' else 'TRUE', QtCore.Qt.EditRole)
        return False


class DateDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(DateDelegate, self).__init__(parent)
        self.model = parent.model

    def createEditor(self, parent, option, index):
        editor = QtGui.QDateEdit(parent)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        editor.setDate(QtCore.QDate.fromString(value, "yyyy-MM-dd"))

    def setModelData(self, editor, model, index):
        value = editor.date().toString("yyyy-MM-dd")
        if (value != ""):
            model.setData(index, value, QtCore.Qt.EditRole)


##Базовый класс таблицы
class TableBase(QtGui.QWidget):
    def __init__(self, model, tabName, parent=None):
        super(TableBase, self).__init__(parent)

        self.name = tabName

        self.view = QtGui.QTableView()
        self.view.setModel(model)
        self.view.setItemDelegateForColumn(0, AutoIncrement(self.view))
        self.view.setSelectionBehavior(QtGui.QTableView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegate(QtSql.QSqlRelationalDelegate(self.view))

        ##Секция кнопок и их связей
        self.insertButton = QtGui.QPushButton(u"Вставить")
        self.insertButton.clicked.connect(self.insert)

        self.removeButton = QtGui.QPushButton(u"Удалить")
        self.removeButton.clicked.connect(self.remove)

        self.updateButton = QtGui.QPushButton(u"Обновить")
        self.updateButton.clicked.connect(self.update)

        self.saveButton = QtGui.QPushButton(u"Сохранить")
        self.saveButton.clicked.connect(self.save)

        self.undoButton = QtGui.QPushButton(u"Отменить")
        self.undoButton.clicked.connect(self.undo)

        self.popMenu = QtGui.QMenu(self.view)
        self.popMenu.addAction(u"Вставить", self.insert)
        self.popMenu.addAction(u"Удалить", self.remove)
        self.popMenu.addSeparator()
        self.popMenu.addAction(u"Обновить", self.update)
        self.popMenu.addAction(u"Сохранить", self.save)
        self.popMenu.addAction(u"Отменить", self.undo)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.view, QtCore.SIGNAL("customContextMenuRequested(const QPoint &)"), self.onContextMenu)

        viewselectionModel = self.view.selectionModel()
        viewselectionModel.selectionChanged.connect(self.updateActions)

        self.view.model().dataChanged.connect(self.dataChanged)

        self.hasUndo = False

        ##Сетка объектов на экране
        buttonsLayout = QtGui.QHBoxLayout()
        buttonsLayout.addWidget(self.insertButton)
        buttonsLayout.addWidget(self.removeButton)
        buttonsLayout.addStretch(1)
        buttonsLayout.addWidget(self.updateButton)
        buttonsLayout.addWidget(self.saveButton)
        buttonsLayout.addWidget(self.undoButton)

        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.addWidget(self.view)
        self.mainLayout.addLayout(buttonsLayout, 1)

        self.readSettings()
        self.updateActions()

    def dataChanged(self):
        self.hasUndo = True
        self.updateActions()

    def insert(self):
        if self.view.selectionModel().currentIndex().isValid():
            row = self.view.currentIndex().row()
            record = self.view.model().record(row)
            record.remove(0)
            self.view.model().insertRow(row)
            self.view.model().setRecord(row, record)
        else:
            row = self.view.model().rowCount()
            record = self.view.model().record()
            record.remove(0)
            self.view.model().insertRow(row)
            self.view.model().setRecord(row, record)
            self.hasUndo = True
            self.updateActions()

    def remove(self):
        model = self.view.model()
        for r in set((i.row() for i in self.view.selectedIndexes())):
            model.removeRow(r)
        self.hasUndo = True
        self.updateActions()

    def update(self):
        self.view.model().select()
        self.hasUndo = False
        self.updateActions()

    def save(self):
        self.view.model().submitAll()
        lastError = self.view.model().lastError()
        if lastError.isValid():
            QtGui.QMessageBox.warning(self, u"Ошибка при запросе", lastError.text(), QtGui.QMessageBox.Ok)
        else:
            self.hasUndo = False
            self.updateActions()

    def undo(self):
        self.view.model().revertAll()
        self.hasUndo = False
        self.updateActions()

    def updateActions(self):
        hasSelection = not self.view.selectionModel().selection().isEmpty()
        hasCurrent = self.view.selectionModel().currentIndex().isValid()
        self.removeButton.setEnabled(hasSelection)
        self.updateButton.setEnabled(self.hasUndo)
        self.saveButton.setEnabled(self.hasUndo)
        self.undoButton.setEnabled(self.hasUndo)

    def onContextMenu(self, point):
        hasSelection = not self.view.selectionModel().selection().isEmpty()
        self.popMenu.actions()[1].setEnabled(hasSelection)
        self.popMenu.actions()[2].setEnabled(self.hasUndo)
        self.popMenu.actions()[3].setEnabled(self.hasUndo)
        self.popMenu.actions()[4].setEnabled(self.hasUndo)
        self.popMenu.exec_(self.view.mapToGlobal(point))

    def readSettings(self):
        settings = QtCore.QSettings(self.view.model().tableName())
        for i in range(self.view.model().columnCount()):
            self.view.setColumnWidth(i, int(settings.value(u"column%d" % i, 60)))

    def writeSettings(self):
        settings = QtCore.QSettings(self.view.model().tableName())
        for i in range(self.view.model().columnCount()):
            settings.setValue(u"column%d" % i, self.view.columnWidth(i))


##Потомки базовой таблицы
class TableGPU(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlTableModel()
        model.setTable(u'GPU')
        model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        model.select()

        super(TableGPU, self).__init__(model, parent)

class TableMRER(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlTableModel()
        model.setTable(u'MRER')
        model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        model.select()

        super(TableMRER, self).__init__(model, parent)

class TableMMR(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlTableModel()
        model.setTable(u'MMR')
        model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        model.select()

        super(TableMMR, self).__init__(model, parent)

class TableGC(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlRelationalTableModel()
        model.setTable(u'GC')
        model.setRelation(2, QtSql.QSqlRelation(u"GPU", u"код", u"название"))
        model.setHeaderData(2, QtCore.Qt.Horizontal, u"граф. проц", QtCore.Qt.DisplayRole)
        model.setRelation(3, QtSql.QSqlRelation(u"MRER", u"код", u"название"))
        model.setHeaderData(3, QtCore.Qt.Horizontal, u"производитель", QtCore.Qt.DisplayRole)
        model.setRelation(4, QtSql.QSqlRelation(u"MMR", u"код", u"объём"))
        model.setHeaderData(4, QtCore.Qt.Horizontal, u"объём памяти", QtCore.Qt.DisplayRole)
        model.setEditStrategy(QtSql.QSqlRelationalTableModel.OnManualSubmit)
        model.select()

        super(TableGC, self).__init__(model, parent)

class TableBUYER(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlTableModel()
        model.setTable(u'BUYER')
        model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        model.select()

        super(TableBUYER, self).__init__(model, parent)

class TablePURCHASE(TableBase):
    def __init__(self, parent=None):
        model = QtSql.QSqlRelationalTableModel()
        model.setTable(u'PURCHASE')
        model.setRelation(4, QtSql.QSqlRelation(u"GC", u"код", u"название"))
        model.setHeaderData(4, QtCore.Qt.Horizontal, u"видеокарта", QtCore.Qt.DisplayRole)
        model.setRelation(5, QtSql.QSqlRelation(u"BUYER", u"код", u"адрес"))
        model.setHeaderData(5, QtCore.Qt.Horizontal, u"адрес покупателя", QtCore.Qt.DisplayRole)
        model.setEditStrategy(QtSql.QSqlRelationalTableModel.OnManualSubmit)
        model.select()

        super(TablePURCHASE, self).__init__(model, parent)
        self.view.setItemDelegateForColumn(1, DateDelegate(self.view))
        self.view.setItemDelegateForColumn(3, BoolDelegate(self.view))


##Главный класс
class AppWGUI(QtGui.QTabWidget):
    def __init__(self, appName, parent=None):
        super(AppWGUI, self).__init__(parent)

        self.setWindowTitle(appName)

        self.tables = [TableGPU(u"Граф. Процессоры"), TableMRER(u"Производители"),\
                        TableMMR(u"Оперативная память"), TableGC(u"Видеокарты"), \
                        TableBUYER(u"Покупатели"), TablePURCHASE(u"Покупки") ]
        for tbl in self.tables:
            self.addTab(tbl, tbl.name)


##int main(){}
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    QtCore.QLocale.setDefault(QtCore.QLocale("ru_RU"))

    sqlDB = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    sqlDB.setDatabaseName(u'gcs.sqlite')
    sqlDB.open()

    dialog = AppWGUI(u"Магазин видеокарт")
    dialog.show()

    sys.exit(app.exec_())