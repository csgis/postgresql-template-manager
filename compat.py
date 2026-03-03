"""
Qt5 / Qt6 compatibility layer for KGR Toolbox.

All scoped enum constants live here. Each file imports what it needs from this module
instead of using Qt enums directly. This keeps compatibility logic in one place.

Qt6 (PyQt6) uses fully scoped enums:  QMessageBox.StandardButton.Ok
Qt5 (PyQt5) uses short-form enums:    QMessageBox.Ok

We try Qt6 first, fall back to Qt5.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QMessageBox, QDialog, QDialogButtonBox,
    QHeaderView, QAbstractItemView, QLineEdit, QTableWidget
)

# ---------------------------------------------------------------------------
# Qt core enums
# ---------------------------------------------------------------------------
try:
    AlignCenter = Qt.AlignmentFlag.AlignCenter
except AttributeError:
    AlignCenter = Qt.AlignCenter

try:
    LeftDockWidgetArea = Qt.DockWidgetArea.LeftDockWidgetArea
except AttributeError:
    LeftDockWidgetArea = Qt.LeftDockWidgetArea

try:
    ItemIsEditable = Qt.ItemFlag.ItemIsEditable
except AttributeError:
    ItemIsEditable = Qt.ItemIsEditable

try:
    RichText = Qt.TextFormat.RichText
except AttributeError:
    RichText = Qt.RichText

try:
    ElideNone = Qt.TextElideMode.ElideNone
except AttributeError:
    ElideNone = Qt.ElideNone

# ---------------------------------------------------------------------------
# QMessageBox enums
# ---------------------------------------------------------------------------
try:
    MsgBoxOk = QMessageBox.StandardButton.Ok
    MsgBoxYes = QMessageBox.StandardButton.Yes
    MsgBoxNo = QMessageBox.StandardButton.No
except AttributeError:
    MsgBoxOk = QMessageBox.Ok
    MsgBoxYes = QMessageBox.Yes
    MsgBoxNo = QMessageBox.No

try:
    MsgBoxIconWarning = QMessageBox.Icon.Warning
except AttributeError:
    MsgBoxIconWarning = QMessageBox.Warning

# ---------------------------------------------------------------------------
# QDialogButtonBox enums
# ---------------------------------------------------------------------------
try:
    ButtonYes = QDialogButtonBox.StandardButton.Yes
    ButtonNo = QDialogButtonBox.StandardButton.No
except AttributeError:
    ButtonYes = QDialogButtonBox.Yes
    ButtonNo = QDialogButtonBox.No

# ---------------------------------------------------------------------------
# QDialog enums
# ---------------------------------------------------------------------------
try:
    DialogAccepted = QDialog.DialogCode.Accepted
except AttributeError:
    DialogAccepted = QDialog.Accepted

# ---------------------------------------------------------------------------
# QHeaderView enums
# ---------------------------------------------------------------------------
try:
    ResizeToContents = QHeaderView.ResizeMode.ResizeToContents
    Stretch = QHeaderView.ResizeMode.Stretch
except AttributeError:
    ResizeToContents = QHeaderView.ResizeToContents
    Stretch = QHeaderView.Stretch

# ---------------------------------------------------------------------------
# QAbstractItemView / QTableWidget enums
# ---------------------------------------------------------------------------
try:
    SelectRows = QAbstractItemView.SelectionBehavior.SelectRows
except AttributeError:
    SelectRows = QAbstractItemView.SelectRows

try:
    SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
except AttributeError:
    SingleSelection = QAbstractItemView.SingleSelection

# ---------------------------------------------------------------------------
# QLineEdit enums
# ---------------------------------------------------------------------------
try:
    EchoPassword = QLineEdit.EchoMode.Password
except AttributeError:
    EchoPassword = QLineEdit.Password

# ---------------------------------------------------------------------------
# Qgis enums (message levels, layer types, writer enums)
# ---------------------------------------------------------------------------
try:
    from qgis.core import Qgis

    try:
        MessageInfo = Qgis.MessageLevel.Info
        MessageCritical = Qgis.MessageLevel.Critical
        MessageWarning = Qgis.MessageLevel.Warning
    except AttributeError:
        MessageInfo = Qgis.Info
        MessageCritical = Qgis.Critical
        MessageWarning = Qgis.Warning

    try:
        LayerTypeVector = Qgis.LayerType.Vector
    except AttributeError:
        # QGIS 3.x: use the integer constant from QgsMapLayer / QgsMapLayerType
        try:
            from qgis.core import QgsMapLayerType
            LayerTypeVector = QgsMapLayerType.VectorLayer
        except ImportError:
            from qgis.core import QgsVectorLayer
            LayerTypeVector = QgsVectorLayer.VectorLayer

except ImportError:
    # Fallback if qgis.core not available (e.g. during linting)
    MessageInfo = 0
    MessageCritical = 2
    MessageWarning = 1
    LayerTypeVector = 0

try:
    from qgis.core import QgsVectorFileWriter

    try:
        WriterNoError = QgsVectorFileWriter.WriterError.NoError
    except AttributeError:
        WriterNoError = QgsVectorFileWriter.NoError

    try:
        CreateOrOverwriteFile = QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
        CreateOrOverwriteLayer = QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
    except AttributeError:
        CreateOrOverwriteFile = QgsVectorFileWriter.CreateOrOverwriteFile
        CreateOrOverwriteLayer = QgsVectorFileWriter.CreateOrOverwriteLayer

    # writeAsVectorFormatV3 was introduced in QGIS 3.10.3; writeAsVectorFormat
    # still exists in 3.x but is removed in 4.x.
    HAS_WRITE_V3 = hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3')

except ImportError:
    WriterNoError = 0
    CreateOrOverwriteFile = 0
    CreateOrOverwriteLayer = 1
    HAS_WRITE_V3 = False
