"""
Databases tab for PostgreSQL Template Manager with database deletion functionality.
Enhanced with comment display and ability to create from templates OR existing databases.
"""

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, 
                                QLineEdit, QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
                                QLabel, QMessageBox, QDialog, QCheckBox, QTextEdit,
                                QFrame, QSizePolicy, QHeaderView, QRadioButton, QButtonGroup)
from qgis.PyQt.QtGui import QFont, QPixmap
from .base_tab import BaseTab
from ..compat import AlignCenter, DialogAccepted, ItemIsEditable, MsgBoxOk, ResizeToContents, RichText, SelectRows, SingleSelection


class DatabaseDeletionDialog(QDialog):
    """
    Single-step confirmation dialog for database deletion with strong warning.
    """
    
    def __init__(self, database_name, database_info, parent=None):
        super().__init__(parent)
        self.database_name = database_name
        self.database_info = database_info
        
        self.setWindowTitle("⚠️ DELETE DATABASE - WARNING")
        self.setModal(True)
        self.setMinimumSize(500, 450)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        
        # Warning header
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #ffebee;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)
        
        # Large warning icon and text
        warning_label = QLabel("⚠️ DANGER: DATABASE DELETION")
        warning_font = QFont()
        warning_font.setPointSize(16)
        warning_font.setBold(True)
        warning_label.setFont(warning_font)
        warning_label.setAlignment(AlignCenter)
        warning_label.setStyleSheet("color: #d32f2f;")
        warning_layout.addWidget(warning_label)
        
        layout.addWidget(warning_frame)
        
        # Database information
        info_label = QLabel("You are about to DELETE the following database:")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-top: 15px;")
        layout.addWidget(info_label)
        
        # Database details
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3e0;
                border-radius: 5px;
                padding: 0px;
                margin: 10px 0;
            }
        """)
        details_layout = QVBoxLayout(details_frame)
        
        db_name_label = QLabel(f"📂 Database Name: {self.database_name}")
        db_name_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #e65100;")
        details_layout.addWidget(db_name_label)
        
        if self.database_info:
            size_label = QLabel(f"💾 Size: {self.database_info.get('size_pretty', 'Unknown')}")
            owner_label = QLabel(f"👤 Owner: {self.database_info.get('owner', 'Unknown')}")
            template_label = QLabel(f"📋 Template: {'Yes' if self.database_info.get('is_template') else 'No'}")
            
            details_layout.addWidget(size_label)
            details_layout.addWidget(owner_label)
            details_layout.addWidget(template_label)
        
        layout.addWidget(details_frame)
        
        # Warning text
        warning_text = QTextEdit()
        warning_text.setReadOnly(True)
        warning_text.setMaximumHeight(120)
        warning_text.setStyleSheet("background-color: #ffebee;")
        warning_text.setPlainText(
            "⚠️ WARNING: This action is IRREVERSIBLE!\n\n"
            "• ALL data in this database will be permanently lost\n"
            "• ALL tables, views, functions, and stored procedures will be deleted\n"
            "• Any applications or services using this database will FAIL\n"
            "• This action cannot be undone - there is no recovery option"
        )
        layout.addWidget(warning_text)
        
        # Confirmation input
        instruction_label = QLabel(f"To confirm deletion, type the database name exactly: {self.database_name}")
        instruction_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin: 15px 0 5px 0;")
        layout.addWidget(instruction_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Type database name here...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 10px;
                border: 2px solid #f44336;
                border-radius: 5px;
                background-color: white;
            }
        """)
        self.name_input.textChanged.connect(self.check_name_match)
        layout.addWidget(self.name_input)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0)
        
        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.delete_button = QPushButton("DELETE DATABASE")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.delete_button.clicked.connect(self.accept)
        self.delete_button.setEnabled(False)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def check_name_match(self):
        """Check if the typed name matches the database name."""
        name_match = self.name_input.text() == self.database_name
        self.delete_button.setEnabled(name_match)
        
        if name_match:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    font-size: 14px;
                    padding: 10px;
                    border: 2px solid #4caf50;
                    border-radius: 5px;
                    background-color: #e8f5e8;
                }
            """)
        else:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    font-size: 14px;
                    padding: 10px;
                    border: 2px solid #f44336;
                    border-radius: 5px;
                    background-color: white;
                }
            """)


class DatabasesTab(BaseTab):
    """Tab for managing databases created from templates or existing databases."""
    
    # Signals
    databases_refreshed = pyqtSignal(list)  # List of database names
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
        self.current_templates = []
        self.current_databases = []
    
    def setup_ui(self):
        """Setup the databases tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("Database Manager")
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
        
        # Create database section
        create_group = QGroupBox("Create Database")
        create_layout = QFormLayout(create_group)
        
        # Source type selection
        source_type_layout = QHBoxLayout()
        self.source_type_group = QButtonGroup()
        
        self.from_template_radio = QRadioButton("From Template")
        self.from_template_radio.setChecked(True)
        self.from_template_radio.toggled.connect(self.on_source_type_changed)
        
        self.from_database_radio = QRadioButton("From Existing Database")
        self.from_database_radio.toggled.connect(self.on_source_type_changed)
        
        self.source_type_group.addButton(self.from_template_radio)
        self.source_type_group.addButton(self.from_database_radio)
        
        source_type_layout.addWidget(self.from_template_radio)
        source_type_layout.addWidget(self.from_database_radio)
        source_type_layout.addStretch()
        
        create_layout.addRow("Source Type:", source_type_layout)
        
        # Source selection combo
        self.source_combo = QComboBox()
        self.source_label = QLabel("Template:")
        create_layout.addRow(self.source_label, self.source_combo)
        
        # New database name
        self.new_db_name_edit = QLineEdit()
        create_layout.addRow("New Database Name:", self.new_db_name_edit)
        
        # Add comment field
        self.db_comment_edit = QLineEdit()
        self.db_comment_edit.setPlaceholderText("Optional description for the database (e.g., 'Development environment for project X')")
        create_layout.addRow("Comment:", self.db_comment_edit)
        
        self.create_db_btn = QPushButton("Create Database")
        self.create_db_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.create_db_btn.clicked.connect(self.create_database)
        
        create_layout.addWidget(self.create_db_btn)
        
        layout.addWidget(create_group)
        
        # Databases management section
        management_group = QGroupBox("Database Management")
        management_layout = QVBoxLayout(management_group)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        self.refresh_databases_btn = QPushButton("Refresh")
        self.refresh_databases_btn.clicked.connect(self.refresh_databases)
        
        self.delete_db_btn = QPushButton("Delete Database")
        self.delete_db_btn.clicked.connect(self.delete_database)
        self.delete_db_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.refresh_databases_btn)
        buttons_layout.addWidget(self.delete_db_btn)
        buttons_layout.addStretch()
        
        management_layout.addLayout(buttons_layout)
        
        # Database table
        self.databases_table = QTableWidget()
        self.databases_table.setColumnCount(2)
        self.databases_table.setHorizontalHeaderLabels(["Database Name", "Comment"])
        self.databases_table.setSelectionBehavior(SelectRows)
        self.databases_table.setSelectionMode(SingleSelection)
        self.databases_table.horizontalHeader().setStretchLastSection(True)
        self.databases_table.horizontalHeader().setSectionResizeMode(0, ResizeToContents)
        self.databases_table.setSortingEnabled(True)
        self.databases_table.itemSelectionChanged.connect(self.on_database_selection_changed)
        management_layout.addWidget(self.databases_table)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        management_layout.addWidget(self.status_label)
        
        layout.addWidget(management_group)

    def on_source_type_changed(self):
        """Handle source type radio button changes."""
        if self.from_template_radio.isChecked():
            self.source_label.setText("Template:")
            self.refresh_source_combo()
        else:
            self.source_label.setText("Source Database:")
            self.refresh_source_combo()

    def refresh_source_combo(self):
        """Refresh the source combo box based on selected source type."""
        current_selection = self.source_combo.currentText()
        self.source_combo.clear()
        
        if self.from_template_radio.isChecked():
            # Show templates
            self.source_combo.addItems(self.current_templates)
            if current_selection in self.current_templates:
                self.source_combo.setCurrentText(current_selection)
        else:
            # Show databases (excluding system databases and current database)
            available_databases = []
            for db_name in self.current_databases:
                if (not self.db_manager.is_system_database(db_name) and 
                    db_name != self.db_manager.connection_params.get('database')):
                    available_databases.append(db_name)
            
            self.source_combo.addItems(available_databases)
            if current_selection in available_databases:
                self.source_combo.setCurrentText(current_selection)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>Database Manager</h3>"
            "<p>Create and manage PostgreSQL databases from templates or existing databases.</p>"
            "<h4>Database Creation:</h4>"
            "<ul>"
            "<li><b>From Template:</b> Creates database from template with empty data</li>"
            "<li><b>From Existing Database:</b> Creates a copy of an existing database</li>"
            "<li><b>Ready to use:</b> Database is immediately available for connections</li>"
            "</ul>"
            "<h4>Database Deletion:</h4>"
            "<ul>"
            "<li><b>IRREVERSIBLE:</b> Once deleted, data cannot be recovered</li>"
            "<li><b>Strong warning:</b> Single confirmation dialog with clear consequences</li>"
            "<li><b>Safety checks:</b> Prevents deletion of system databases</li>"
            "</ul>"
            "<h4>Database Comments:</h4>"
            "<ul>"
            "<li><b>Documentation:</b> Comments help identify database purpose and content</li>"
            "<li><b>Metadata:</b> Comments are stored in PostgreSQL's system catalog</li>"
            "</ul>"
            "<h4>Database Creation Process:</h4>"
            "<ol>"
            "<li><b>Choose source type:</b> Select template or existing database</li>"
            "<li><b>Select source:</b> Choose from available templates or databases</li>"
            "<li><b>Name database:</b> Enter a unique name (letters, numbers, underscores only)</li>"
            "<li><b>Create:</b> PostgreSQL creates the new database</li>"
            "</ol>"
            "<h4>Database Deletion Process:</h4>"
            "<ol>"
            "<li><b>Select database:</b> Choose database from the list</li>"
            "<li><b>Type database name:</b> Confirm by typing exact database name</li>"
            "<li><b>Permanent deletion:</b> Database is immediately destroyed</li>"
            "</ol>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - Database Manager")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        msg.resize(700, 600)
        msg.exec()
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def on_database_selection_changed(self):
        """Handle database selection change."""
        current_row = self.databases_table.currentRow()
        has_selection = current_row != -1
        
        self.delete_db_btn.setEnabled(has_selection)
        
        if has_selection:
            db_name_item = self.databases_table.item(current_row, 0)
            
            if db_name_item:
                db_name = db_name_item.text()
                self.status_label.setText(f"Selected: {db_name}")
                
                # Check if it's a system database or currently connected
                if self.db_manager.is_system_database(db_name):
                    self.delete_db_btn.setEnabled(False)
                    self.status_label.setText(f"Selected: {db_name} (System database - cannot delete)")
                elif self.db_manager.connection_params.get('database') == db_name:
                    self.delete_db_btn.setEnabled(False)
                    self.status_label.setText(f"Selected: {db_name} (Currently connected - cannot delete)")
        else:
            self.status_label.setText("No database selected")
    
    def refresh_databases(self):
        """Refresh databases table with comments."""
        if not self.check_connection():
            return
        
        try:
            databases_with_comments = self.db_manager.get_databases_with_comments()
            self.databases_table.setRowCount(0)  # Clear existing rows
            
            database_names = []
            for row, (db_name, comment) in enumerate(databases_with_comments):
                database_names.append(db_name)
                
                # Insert new row
                self.databases_table.insertRow(row)
                
                # Database name item
                name_item = QTableWidgetItem(db_name)
                name_item.setFlags(name_item.flags() & ~ItemIsEditable)  # Make read-only
                self.databases_table.setItem(row, 0, name_item)
                
                # Comment item
                comment_text = comment if comment else "(No comment)"
                comment_item = QTableWidgetItem(comment_text)
                comment_item.setFlags(comment_item.flags() & ~ItemIsEditable)  # Make read-only
                self.databases_table.setItem(row, 1, comment_item)
            
            # Update current databases list
            self.current_databases = database_names
            
            # Refresh source combo if showing databases
            if self.from_database_radio.isChecked():
                self.refresh_source_combo()
            
            self.emit_log(f"Refreshed databases: {len(databases_with_comments)} found")
            self.databases_refreshed.emit(database_names)
        except Exception as e:
            self.emit_log(f"Error refreshing databases: {str(e)}")
    
    def refresh_templates(self, templates):
        """Refresh templates list."""
        self.current_templates = templates
        
        # Refresh source combo if showing templates
        if self.from_template_radio.isChecked():
            self.refresh_source_combo()
    
    def create_database(self):
        """Create database from selected template or existing database."""
        if not self.check_connection():
            return
        
        source_name = self.source_combo.currentText()
        new_db_name = self.new_db_name_edit.text().strip()
        db_comment = self.db_comment_edit.text().strip()
        
        if not self.validate_selection(self.source_combo, "source"):
            return
        
        if not self.validate_non_empty_field(new_db_name, "database name"):
            return
        
        # Check if database name is valid (basic validation)
        if not self._is_valid_database_name(new_db_name):
            self.show_warning("Invalid database name. Use only letters, numbers, and underscores.")
            return
        
        # Check if database already exists
        if self.db_manager.database_exists(new_db_name):
            self.show_warning(f"Database '{new_db_name}' already exists. Please choose a different name.")
            return
        
        # Check privileges
        if not self.check_user_privileges():
            return
        
        self.emit_progress_started()
        
        if self.from_template_radio.isChecked():
            # Create from template
            self.db_manager.create_database_from_template(source_name, new_db_name, db_comment)
        else:
            # Create from existing database
            # Check if the database manager has the method for creating from database
            if hasattr(self.db_manager, 'create_database_from_database'):
                self.db_manager.create_database_from_database(source_name, new_db_name, db_comment)
            else:
                # Fallback: use template method with a warning
                self.emit_log("⚠️ Warning: Creating database copy using template method")
                self.db_manager.create_database_from_template(source_name, new_db_name, db_comment)
    
    def delete_database(self):
        """Delete selected database with confirmation."""
        if not self.check_connection():
            return
        
        current_row = self.databases_table.currentRow()
        if current_row == -1:
            self.show_warning("Please select a database to delete.")
            return
        
        # Get the database name from the first column
        db_name_item = self.databases_table.item(current_row, 0)
        
        if not db_name_item:
            self.show_warning("Could not retrieve database information.")
            return
        
        db_name = db_name_item.text()
        
        # Check if it's a system database or currently connected
        if self.db_manager.is_system_database(db_name):
            self.show_warning("Cannot delete system databases.")
            return
        elif self.db_manager.connection_params.get('database') == db_name:
            self.show_warning("Cannot delete the currently connected database.")
            return
        
        # Get database info for the confirmation dialog
        db_info = self.db_manager.get_database_info(db_name)
        
        # Show the confirmation dialog
        dialog = DatabaseDeletionDialog(db_name, db_info, self)
        result = dialog.exec()
        
        if result == DialogAccepted:
            # User confirmed deletion - execute immediately
            self.emit_progress_started()
            self.emit_log(f"🔥 DELETING database '{db_name}'")
            self.db_manager.delete_database(db_name, force_drop_connections=True)
        else:
            self.emit_log(f"Database deletion cancelled by user.")
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if any(keyword in message.lower() for keyword in ["database", "template"]):
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✅ {message}")
                
                # Clear form and refresh if it was a creation
                if "created successfully" in message.lower():
                    self.new_db_name_edit.clear()
                    self.db_comment_edit.clear()
                
                # Refresh databases list for any database operation
                self.refresh_databases()
            else:
                self.emit_log(f"❌ {message}")
    
    def get_database_names(self):
        """Get list of current database names."""
        database_names = []
        for row in range(self.databases_table.rowCount()):
            name_item = self.databases_table.item(row, 0)
            if name_item:
                database_names.append(name_item.text())
        return database_names
    
    def _is_valid_database_name(self, name):
        """Validate database name format."""
        import re
        # PostgreSQL database names: letters, numbers, underscores, start with letter/underscore
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, name)) and len(name) <= 63