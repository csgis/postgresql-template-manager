"""
Base tab class with common functionality for PostgreSQL Template Manager tabs.
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget, QMessageBox
from ..compat import MsgBoxNo, MsgBoxYes


class BaseTab(QWidget):
    """Base class for all tab widgets."""
    
    # Signals
    log_message = pyqtSignal(str)
    progress_started = pyqtSignal()
    progress_finished = pyqtSignal()
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_dialog = parent
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the user interface. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def connect_signals(self):
        """Connect signals. Can be overridden by subclasses."""
        pass
    
    def check_connection(self):
        """Check if database connection is established."""
        if not self.db_manager.connection_params:
            QMessageBox.warning(self, "Warning", "Please test the connection first.")
            return False
        return True
    
    def show_warning(self, message):
        """Show warning message."""
        QMessageBox.warning(self, "Warning", message)
    
    def show_error(self, message):
        """Show error message."""
        QMessageBox.critical(self, "Error", message)
    
    def show_info(self, message):
        """Show info message."""
        QMessageBox.information(self, "Information", message)
    
    def confirm_action(self, title, message):
        """Show confirmation dialog."""
        reply = QMessageBox.question(self, title, message,
                                   MsgBoxYes | MsgBoxNo)
        return reply == MsgBoxYes
    
    def emit_log(self, message):
        """Emit log message signal."""
        self.log_message.emit(message)
    
    def emit_progress_started(self):
        """Emit progress started signal."""
        self.progress_started.emit()
    
    def emit_progress_finished(self):
        """Emit progress finished signal."""
        self.progress_finished.emit()
    
    def check_user_privileges(self, required_privilege='can_create_db'):
        """Check if user has required privileges."""
        privileges = self.db_manager.check_user_privileges()
        
        if required_privilege == 'can_create_db':
            if not privileges['can_create_db'] and not privileges['is_superuser']:
                self.show_error("Insufficient privileges. CREATEDB permission required.")
                return False
        
        return True
    
    def validate_non_empty_field(self, field_value, field_name):
        """Validate that a field is not empty."""
        if not field_value.strip():
            self.show_warning(f"Please enter a {field_name}.")
            return False
        return True
    
    def validate_selection(self, combo_box, field_name):
        """Validate that a combo box has a selection."""
        if not combo_box.currentText():
            self.show_warning(f"Please select a {field_name}.")
            return False
        return True