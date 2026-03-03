"""
Connection tab for PostgreSQL Template Manager.
"""

from qgis.PyQt.QtCore import QSettings, pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
                                QSpinBox, QPushButton, QLabel, QMessageBox)
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab
from ..compat import EchoPassword, MsgBoxOk, RichText


class ConnectionTab(BaseTab):
    """Tab for managing database connections."""
    
    # Signals
    connection_status_changed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
        self.load_settings()
    
    def setup_ui(self):
        """Setup the connection tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("PostgreSQL Connection")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        self.help_btn = QPushButton("Help")
        self.help_btn.setFixedWidth(80)
        self.help_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #2196F3; "
            "color: white; "
            "font-weight: bold; "
            "padding: 5px 10px; "
            "border: none; "
            "border-radius: 4px; "
            "font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.help_btn.clicked.connect(self._show_help_popup)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.help_btn)
        layout.addLayout(title_layout)
        
        # Connection form
        form_layout = QFormLayout()
        
        # Connection parameters
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(5432)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(EchoPassword)
        
        form_layout.addRow("Host:", self.host_edit)
        form_layout.addRow("Port:", self.port_edit)
        form_layout.addRow("Username:", self.username_edit)
        form_layout.addRow("Password:", self.password_edit)
        
        # Test connection button
        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self.test_connection)
        form_layout.addWidget(self.test_conn_btn)
        
        # Connection status
        self.conn_status = QLabel("Not connected")
        self.conn_status.setStyleSheet("color: red;")
        form_layout.addWidget(self.conn_status)
        
        layout.addLayout(form_layout)
        layout.addStretch()

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>PostgreSQL Connection</h3>"
            "<p>Configure connection settings to connect to your PostgreSQL database server.</p>"
            "<h4>Connection Parameters:</h4>"
            "<ul>"
            "<li><b>Host:</b> Server address (localhost, IP address, or domain name)</li>"
            "<li><b>Port:</b> PostgreSQL port number (default: 5432)</li>"
            "<li><b>Username:</b> PostgreSQL user account with appropriate privileges</li>"
            "<li><b>Password:</b> Password for the specified user account</li>"
            "</ul>"
            "<h4>Required Privileges:</h4>"
            "<p>Your PostgreSQL user needs these permissions for full functionality:</p>"
            "<ul>"
            "<li><b>CREATEDB:</b> Create new databases and templates</li>"
            "<li><b>Login rights:</b> Connect to the PostgreSQL server</li>"
            "<li><b>Schema access:</b> Read project data from existing databases</li>"
            "<li><b>Connection termination:</b> Drop active connections when needed</li>"
            "</ul>"
            "<h4>Connection Tips:</h4>"
            "<ul>"
            "<li><b>Local connections:</b> Use 'localhost' or '127.0.0.1' for same-machine databases</li>"
            "<li><b>Remote connections:</b> Ensure PostgreSQL accepts remote connections</li>"
            "<li><b>Firewall:</b> Check that port 5432 (or custom port) is accessible</li>"
            "<li><b>SSL:</b> Connection uses standard PostgreSQL security settings</li>"
            "</ul>"
            "<h4>Troubleshooting:</h4>"
            "<ul>"
            "<li><b>Connection refused:</b> Check if PostgreSQL is running and port is correct</li>"
            "<li><b>Authentication failed:</b> Verify username and password</li>"
            "<li><b>Permission denied:</b> User may lack required database privileges</li>"
            "<li><b>Timeout:</b> Network or firewall may be blocking the connection</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - PostgreSQL Connection")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        msg.exec()
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def test_connection(self):
        """Test database connection."""
        host = self.host_edit.text().strip()
        port = self.port_edit.value()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        # Validate required fields
        if not self.validate_non_empty_field(host, "host"):
            return
        if not self.validate_non_empty_field(username, "username"):
            return
        
        self.db_manager.set_connection_params(
            host, port, 'postgres', username, password
        )
        
        self.emit_progress_started()
        self.db_manager.test_connection()
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        self.emit_progress_finished()
        
        if "Connection" in message:
            if success:
                self.conn_status.setText("Connected")
                self.conn_status.setStyleSheet("color: green;")
                self.emit_log(f"✓ {message}")
                self.save_settings()
            else:
                self.conn_status.setText("Connection failed")
                self.conn_status.setStyleSheet("color: red;")
                self.emit_log(f"✗ {message}")
            
            self.connection_status_changed.emit(success, message)
    
    def get_connection_params(self):
        """Get current connection parameters."""
        return {
            'host': self.host_edit.text().strip(),
            'port': self.port_edit.value(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip()
        }
    
    def is_connected(self):
        """Check if currently connected."""
        return bool(self.db_manager.connection_params)
    
    def save_settings(self):
        """Save connection settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        settings.setValue("host", self.host_edit.text())
        settings.setValue("port", self.port_edit.value())
        settings.setValue("username", self.username_edit.text())
        settings.endGroup()
    
    def load_settings(self):
        """Load connection settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        self.host_edit.setText(settings.value("host", "localhost"))
        self.port_edit.setValue(int(settings.value("port", 5432)))
        self.username_edit.setText(settings.value("username", ""))
        settings.endGroup()