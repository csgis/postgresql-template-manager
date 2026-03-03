"""
Templates tab for PostgreSQL Template Manager.
Enhanced with connection handling and user warnings.
"""

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QComboBox, QLineEdit, QPushButton, QGroupBox,
                                QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QDialogButtonBox,
                                QLabel, QTextEdit, QHeaderView, QCheckBox)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab
from ..compat import ButtonNo, ButtonYes, DialogAccepted, ItemIsEditable, MsgBoxNo, MsgBoxOk, MsgBoxYes, ResizeToContents, RichText, SelectRows, SingleSelection


class ConnectionWarningDialog(QDialog):
    """Dialog to warn user about dropping connections."""
    
    def __init__(self, database_name, connection_count, connections_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drop Database Connections")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Warning message
        warning_label = QLabel(
            f"<b>Warning:</b> Creating a template from database '<b>{database_name}</b>' "
            f"requires dropping all active connections.\n\n"
            f"<b>{connection_count}</b> active connection(s) found and will be terminated."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("QLabel { color: #d32f2f; margin: 10px; }")
        layout.addWidget(warning_label)
        
        # Connection details
        if connections_info:
            details_label = QLabel("Active connections that will be dropped:")
            details_label.setStyleSheet("font-weight: bold; margin: 10px;")
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            
            connection_details = []
            for conn_info in connections_info:
                pid, username, client_addr, client_hostname, client_port, backend_start, state, query = conn_info
                client_display = client_addr or client_hostname or "local"
                connection_details.append(
                    f"• PID: {pid}, User: {username}, Client: {client_display}, "
                    f"State: {state}, Started: {backend_start}"
                )
            
            details_text.setPlainText("\n".join(connection_details))
            layout.addWidget(details_text)
        
        # Confirmation message
        confirm_label = QLabel(
            "This action will:\n"
            "• Terminate all active connections to the database\n"
            "• Create a new template with the database structure\n"
            "• Remove all data from the template\n\n"
            "Do you want to continue?"
        )
        confirm_label.setWordWrap(True)
        confirm_label.setStyleSheet("margin: 10px;")
        layout.addWidget(confirm_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            ButtonYes | ButtonNo,
            parent=self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style the buttons
        yes_button = button_box.button(ButtonYes)
        yes_button.setText("Yes, Drop Connections and Create Template")
        yes_button.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; padding: 5px; }")
        
        no_button = button_box.button(ButtonNo)
        no_button.setText("Cancel")
        no_button.setStyleSheet("QPushButton { padding: 5px; }")
        
        layout.addWidget(button_box)


class TemplatesTab(BaseTab):
    """Tab for managing database templates."""
    
    # Signals
    templates_refreshed = pyqtSignal(list)  # List of template names
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the templates tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("PostgreSQL Template Manager")
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
        
        # Create template section
        create_group = QGroupBox("Create Template")
        create_layout = QFormLayout(create_group)
        
        self.source_db_combo = QComboBox()
        self.template_name_edit = QLineEdit()
        
        # Add comment field
        self.template_comment_edit = QLineEdit()
        self.template_comment_edit.setPlaceholderText("Optional description for the template (e.g., 'Production schema template for project X')")
        
        # Add checkbox for qgis_projects table protection
        self.protect_qgis_projects_checkbox = QCheckBox("Preserve qgis_projects table data")
        self.protect_qgis_projects_checkbox.setChecked(True)  # Default checked
        self.protect_qgis_projects_checkbox.setToolTip("When checked, the 'qgis_projects' table will not be truncated and its data will be preserved in the template")
        
        # Add input for schema exclusions
        self.exclude_schemas_edit = QLineEdit()
        self.exclude_schemas_edit.setText("listen")  # Prefill with "listen"
        self.exclude_schemas_edit.setPlaceholderText("Comma-separated list of schemas to preserve (e.g., listen, metadata, system)")
        self.exclude_schemas_edit.setToolTip("Enter schema names separated by commas. Tables in these schemas will not be truncated and their data will be preserved in the template")
        
        self.create_template_btn = QPushButton("Create Template")
        self.create_template_btn.clicked.connect(self.create_template)
        
        create_layout.addRow("Source Database:", self.source_db_combo)
        create_layout.addRow("Template Name:", self.template_name_edit)
        create_layout.addRow("Comment:", self.template_comment_edit)
        create_layout.addRow("", self.protect_qgis_projects_checkbox)
        create_layout.addRow("Exclude Schemas <br>from truncate:", self.exclude_schemas_edit)
        create_layout.addWidget(self.create_template_btn)
        
        layout.addWidget(create_group)
        
        # Templates list section
        list_group = QGroupBox("Existing Templates")
        list_layout = QVBoxLayout(list_group)
        
        # Refresh and delete buttons
        btn_layout = QHBoxLayout()
        self.refresh_templates_btn = QPushButton("Refresh")
        self.refresh_templates_btn.clicked.connect(self.refresh_templates)
        self.delete_template_btn = QPushButton("Delete Selected")
        self.delete_template_btn.clicked.connect(self.delete_template)
        
        btn_layout.addWidget(self.refresh_templates_btn)
        btn_layout.addWidget(self.delete_template_btn)
        list_layout.addLayout(btn_layout)
        
        # Templates table
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(2)
        self.templates_table.setHorizontalHeaderLabels(["Template Name", "Comment"])
        self.templates_table.setSelectionBehavior(SelectRows)
        self.templates_table.setSelectionMode(SingleSelection)
        self.templates_table.horizontalHeader().setStretchLastSection(True)
        self.templates_table.horizontalHeader().setSectionResizeMode(0, ResizeToContents)
        self.templates_table.setSortingEnabled(True)
        list_layout.addWidget(self.templates_table)
        
        layout.addWidget(list_group)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>PostgreSQL Template Manager</h3>"
            "<p>Create and manage PostgreSQL database templates for rapid deployment of pre-configured databases.</p>"
            "<h4>What is a PostgreSQL Template?</h4>"
            "<p>A <b>template database</b> is a blueprint used to create new databases with a predefined structure, "
            "including tables, views, functions, and extensions, but <b>without any data</b>.</p>"
            "<h4>How this tool works:</h4>"
            "<ol>"
            "<li><b>Select source database:</b> Choose an existing database with the desired structure</li>"
            "<li><b>Name the template:</b> Give your template a descriptive name</li>"
            "<li><b>Add comment (optional):</b> Provide a description to help identify the template's purpose, "
            "such as 'Production schema for customer management system' or 'Development environment template'</li>"
            "<li><b>Configure data preservation:</b> Choose which tables/schemas to preserve data from</li>"
            "<li><b>Structure copied:</b> All tables, views, functions, indexes are copied</li>"
            "<li><b>Data handling:</b> By default, template contains no records, but you can preserve specific tables/schemas</li>"
            "<li><b>Template ready:</b> Use template to create new databases instantly</li>"
            "</ol>"
            "<h4>Data Preservation Options:</h4>"
            "<ul>"
            "<li><b>Preserve qgis_projects table:</b> When checked, the 'qgis_projects' table data will be kept in the template</li>"
            "<li><b>Exclude Schemas:</b> Comma-separated list of schema names whose tables will not be truncated</li>"
            "</ul>"
            "<h4>Template Comments:</h4>"
            "<p>The <b>comment field</b> allows you to add a descriptive note to your template that will be stored "
            "in the PostgreSQL database catalog. This helps you and other users understand the purpose and content. </p>"
            "<h4>⚠️ Important notes:</h4>"
            "<ul>"
            "<li><b>Active connections:</b> All connections to source database will be dropped during creation</li>"
            "<li><b>Structure preserved:</b> Templates preserve schema and optionally selected data</li>"
            "<li><b>Schema exclusions:</b> Tables in excluded schemas will keep their data in the template</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - PostgreSQL Template Manager")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        msg.exec()
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def refresh_templates(self):
        """Refresh templates table with comments."""
        if not self.check_connection():
            return
        
        try:
            templates_with_comments = self.db_manager.get_templates_with_comments()
            self.templates_table.setRowCount(0)  # Clear existing rows
            
            template_names = []
            for row, (template_name, comment) in enumerate(templates_with_comments):
                template_names.append(template_name)
                
                # Debug: Log what we're getting
                self.emit_log(f"Debug: Template '{template_name}', Comment: '{comment}'")
                
                # Insert new row
                self.templates_table.insertRow(row)
                
                # Template name item
                name_item = QTableWidgetItem(template_name)
                name_item.setFlags(name_item.flags() & ~ItemIsEditable)  # Make read-only
                self.templates_table.setItem(row, 0, name_item)
                
                # Comment item
                comment_text = comment if comment else "(No comment)"
                comment_item = QTableWidgetItem(comment_text)
                comment_item.setFlags(comment_item.flags() & ~ItemIsEditable)  # Make read-only
                self.templates_table.setItem(row, 1, comment_item)
            
            self.emit_log(f"Refreshed templates: {len(templates_with_comments)} found")
            self.templates_refreshed.emit(template_names)
        except Exception as e:
            self.emit_log(f"Error refreshing templates: {str(e)}")
    
    def refresh_source_databases(self, databases):
        """Refresh source databases combo box."""
        self.source_db_combo.clear()
        self.source_db_combo.addItems(databases)
    
    def create_template(self):
        """Create template from selected database."""
        if not self.check_connection():
            return
        
        source_db = self.source_db_combo.currentText()
        template_name = self.template_name_edit.text().strip()
        template_comment = self.template_comment_edit.text().strip()
        
        # Get the new options
        preserve_qgis_projects = self.protect_qgis_projects_checkbox.isChecked()
        exclude_schemas_text = self.exclude_schemas_edit.text().strip()
        
        # Parse excluded schemas
        excluded_schemas = []
        if exclude_schemas_text:
            excluded_schemas = [schema.strip() for schema in exclude_schemas_text.split(",") if schema.strip()]
        
        if not self.validate_selection(self.source_db_combo, "source database"):
            return
        
        if not self.validate_non_empty_field(template_name, "template name"):
            return
        
        # Check privileges
        if not self.check_user_privileges():
            return
        
        # Check for active connections
        try:
            connection_count = self.db_manager.get_connection_count(source_db)
            
            if connection_count > 0:
                # Get detailed connection information
                connections_info = self.db_manager.get_active_connections(source_db)
                
                # Show warning dialog
                dialog = ConnectionWarningDialog(
                    source_db, 
                    connection_count, 
                    connections_info, 
                    self
                )
                
                if dialog.exec() != DialogAccepted:
                    self.emit_log("Template creation cancelled by user")
                    return
                
                self.emit_log(f"User confirmed dropping {connection_count} connections to '{source_db}'")
            else:
                # No active connections, but still show a confirmation
                confirmation_text = f"Create template '{template_name}' from database '{source_db}'?\n\n"
                confirmation_text += "This will create a copy of the database structure with selected data preservation options."
                
                if template_comment:
                    confirmation_text += f"\n\nComment: {template_comment}"
                
                # Add information about data preservation
                if preserve_qgis_projects or excluded_schemas:
                    confirmation_text += "\n\nData preservation settings:"
                    if preserve_qgis_projects:
                        confirmation_text += "\n• qgis_projects table data will be preserved"
                    if excluded_schemas:
                        confirmation_text += f"\n• Schemas excluded from truncation: {', '.join(excluded_schemas)}"
                else:
                    confirmation_text += "\n\nAll table data will be removed (standard template behavior)."
                
                reply = QMessageBox.question(
                    self,
                    "Create Template",
                    confirmation_text,
                    MsgBoxYes | MsgBoxNo,
                    MsgBoxNo
                )
                
                if reply != MsgBoxYes:
                    return
            
            # Proceed with template creation
            self.emit_progress_started()
            self.db_manager.create_template(
                source_db, 
                template_name, 
                template_comment,
                preserve_qgis_projects=preserve_qgis_projects,
                excluded_schemas=excluded_schemas
            )
            
        except Exception as e:
            self.emit_log(f"Error checking connections: {str(e)}")
            self.show_warning(f"Error checking database connections: {str(e)}")
    
    def delete_template(self):
        """Delete selected template."""
        if not self.check_connection():
            return
        
        current_row = self.templates_table.currentRow()
        if current_row == -1:
            self.show_warning("Please select a template to delete.")
            return
        
        # Get the template name from the first column
        template_name_item = self.templates_table.item(current_row, 0)
        if not template_name_item:
            self.show_warning("Could not retrieve template name.")
            return
        
        template_name = template_name_item.text()
        
        if self.confirm_action("Confirm Delete", 
                              f"Are you sure you want to delete template '{template_name}'?\n"
                              "This action cannot be undone!"):
            self.emit_progress_started()
            self.db_manager.delete_template(template_name)
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if any(keyword in message for keyword in ["template", "Template"]):
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✓ {message}")
                self.template_name_edit.clear()
                self.template_comment_edit.clear()
                # Reset data preservation options to defaults
                self.protect_qgis_projects_checkbox.setChecked(True)
                self.exclude_schemas_edit.setText("listen")
                self.refresh_templates()
            else:
                self.emit_log(f"✗ {message}")
    
    def get_template_names(self):
        """Get list of current template names."""
        template_names = []
        for row in range(self.templates_table.rowCount()):
            name_item = self.templates_table.item(row, 0)
            if name_item:
                template_names.append(name_item.text())
        return template_names