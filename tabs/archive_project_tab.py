"""
Archive Project tab for PostgreSQL Template Manager.
Custom portable QGIS project exporter (no libqfieldsync).
"""

import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox, QCheckBox, QSpinBox, QTextEdit
)
from qgis.PyQt.QtGui import QFont
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter, Qgis

from .base_tab import BaseTab
from ..compat import CreateOrOverwriteFile, CreateOrOverwriteLayer, HAS_WRITE_V3, LayerTypeVector, MsgBoxIconWarning, MsgBoxOk, RichText, WriterNoError

class ArchiveProjectTab(BaseTab):
    project_archived = pyqtSignal(str)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Reduce spacing between elements
        layout.setContentsMargins(20, 20, 20, 20)  # Add margins around the whole layout

        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("Portable Project Archiver")
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

        # Output folder section
        folder_group = QVBoxLayout()
        folder_group.setSpacing(8)
        
        folder_label = QLabel("Output Folder:")
        folder_label.setStyleSheet("font-weight: bold;")
        folder_group.addWidget(folder_label)
        
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Select output folder...")
        self.browse_folder_btn = QPushButton("Browse…")
        self.browse_folder_btn.setFixedWidth(80)
        folder_layout.addWidget(self.output_folder_edit)
        folder_layout.addWidget(self.browse_folder_btn)
        folder_group.addLayout(folder_layout)
        
        layout.addLayout(folder_group)

        # Image resize options section
        image_group = QVBoxLayout()
        image_group.setSpacing(8)
        
        # Resize images checkbox
        self.resize_images_checkbox = QCheckBox("Resize images")
        self.resize_images_checkbox.setStyleSheet("font-weight: bold;")
        self.resize_images_checkbox.toggled.connect(self._on_resize_checkbox_toggled)
        if not HAS_PIL:
            self.resize_images_checkbox.setEnabled(False)
            self.resize_images_checkbox.setToolTip(
                "Pillow (PIL) is not installed. Install with:\n"
                "  pip install Pillow\n"
                "or in the OSGeo4W shell:\n"
                "  python -m pip install Pillow")
        image_group.addWidget(self.resize_images_checkbox)
        
        # Pixel size input
        pixel_layout = QHBoxLayout()
        pixel_layout.setSpacing(10)
        self.pixel_label = QLabel("Pixel of long side:")
        self.pixel_label.setEnabled(False)
        self.pixel_spinbox = QSpinBox()
        self.pixel_spinbox.setRange(100, 10000)
        self.pixel_spinbox.setValue(300)
        self.pixel_spinbox.setSuffix(" px")
        self.pixel_spinbox.setEnabled(False)
        pixel_layout.addWidget(self.pixel_label)
        pixel_layout.addWidget(self.pixel_spinbox)
        pixel_layout.addStretch()
        image_group.addLayout(pixel_layout)
        
        # Warning label
        self.resize_warning_label = QLabel("⚠️ Resizing many images can take considerable time")
        self.resize_warning_label.setStyleSheet("color: #FF9800; font-size: 11px; font-style: italic;")
        self.resize_warning_label.setVisible(False)
        image_group.addWidget(self.resize_warning_label)
        
        layout.addLayout(image_group)

        # Archive notes section
        notes_group = QVBoxLayout()
        notes_group.setSpacing(8)
        
        notes_label = QLabel("Archive Notes (optional):")
        notes_label.setStyleSheet("font-weight: bold;")
        notes_group.addWidget(notes_label)
        
        self.notes_textedit = QTextEdit()
        self.notes_textedit.setPlaceholderText("Enter optional notes about this archive (e.g., purpose, context, modifications made)...")
        self.notes_textedit.setMaximumHeight(80)
        self.notes_textedit.setStyleSheet(
            "QTextEdit { "
            "border: 1px solid #ddd; "
            "border-radius: 4px; "
            "padding: 8px; "
            "font-size: 12px; "
            "}"
        )
        notes_group.addWidget(self.notes_textedit)
        
        layout.addLayout(notes_group)

        # Archive button
        self.archive_btn = QPushButton("Create Portable Archive")
        self.archive_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 10px 20px; "
            "border: none; "
            "border-radius: 5px; "
            "font-size: 14px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.archive_btn.setFixedHeight(45)
        layout.addWidget(self.archive_btn)

        # Progress section
        progress_group = QVBoxLayout()
        progress_group.setSpacing(5)
        
        self.progress_label = QLabel("Processing...")
        self.progress_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        self.progress_label.setVisible(False)
        progress_group.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { "
            "border: 2px solid #ddd; "
            "border-radius: 5px; "
            "text-align: center; "
            "font-weight: bold; "
            "} "
            "QProgressBar::chunk { "
            "background-color: #2196F3; "
            "border-radius: 3px; "
            "}"
        )
        self.progress_bar.setFixedHeight(25)
        progress_group.addWidget(self.progress_bar)
        
        layout.addLayout(progress_group)

        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set default output folder
        self._set_default_output_folder()
        
        self.setLayout(layout)

    def _on_resize_checkbox_toggled(self, checked):
        """Handle resize checkbox toggle"""
        self.pixel_label.setEnabled(checked)
        self.pixel_spinbox.setEnabled(checked)
        self.resize_warning_label.setVisible(checked)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>Portable Project Archiver</h3>"
            "<p>Creates a completely self-contained, portable version of your current QGIS project.</p>"
            "<h4>What happens during archiving:</h4>"
            "<ul>"
            "<li><b>PostgreSQL layers →</b> Converted to a single 'data.gpkg' GeoPackage file</li>"
            "<li><b>All project files →</b> Copied to output folder (including DCIM, photos, etc.)</li>"
            "<li><b>Project file →</b> Updated to reference local GeoPackage instead of database</li>"
            "<li><b>Credentials →</b> Database credentials automatically removed for security</li>"
            "<li><b>Folder structure →</b> Preserved exactly as in original project</li>"
            "</ul>"
            "<h4>Image Resizing (Optional):</h4>"
            "<ul>"
            "<li><b>Resize images →</b> If enabled, resizes all images in DCIM folders</li>"
            "<li><b>Long side limit →</b> Images are resized only if their long side exceeds the specified pixel limit</li>"
            "<li><b>Supported formats →</b> JPEG, PNG, TIFF, BMP, and other common image formats</li>"
            "<li><b>Quality preserved →</b> JPEG quality is maintained at 95% during resizing</li>"
            "</ul>"
            "<h4>Result:</h4>"
            "<p>A <b>'{project_name}_portable.qgs'</b> file that can be opened on any computer without needing PostgreSQL access.</p>"
            "<p>An <b>'archive_report.txt'</b> file is also created with details about the archiving process, including date, source project, and any user notes.</p>"
            "<h4>⚠️ Important notes:</h4>"
            "<ul>"
            "<li><b>Large files:</b> DCIM folders and media files will be copied (may take time)</li>"
            "<li><b>Image resizing:</b> Processing many high-resolution images can take significant time</li>"
            "<li><b>Database snapshots:</b> Data reflects the current state at export time</li>"
            "<li><b>No live sync:</b> Archived data won't update from the original database</li>"
            "<li><b>Security:</b> All database credentials are automatically removed</li>"
            "<li><b>Path review:</b> Some absolute file paths may require manual review</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - Portable Project Archiver")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        msg.exec()

    def connect_signals(self):
        self.browse_folder_btn.clicked.connect(self._browse_output_folder)
        self.archive_btn.clicked.connect(self._on_archive_project)

    def _browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_folder_edit.text() or os.path.expanduser("~")
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.emit_log(f"Output folder set to: {folder}")

    def _create_archive_report(self, output_folder, project_file, resized_images_count=0):
        """Create an archive report file with details about the archiving process"""
        try:
            from datetime import datetime
            
            report_path = Path(output_folder) / "archive_report.txt"
            
            # Get current date and time
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get project information
            project_name = os.path.splitext(os.path.basename(project_file))[0]
            project_path = str(project_file)
            
            # Get user notes
            user_notes = self.notes_textedit.toPlainText().strip()
            
            # Create report content
            report_lines = [
                "QGIS PORTABLE PROJECT ARCHIVE REPORT",
                "=" * 45,
                "",
                f"Archive Date: {current_datetime}",
                f"Source Project: {project_name}",
                f"Source Path: {project_path}",
                f"Output Folder: {output_folder}",
                "",
                "PROCESSING DETAILS:",
                "- PostgreSQL layers converted to GeoPackage format",
                "- All project files and folders copied to output directory",
                "- Project file updated to reference local data sources",
                "- Database credentials removed for security",
                "- All PostgreSQL references converted to GeoPackage",
            ]
            
            # Add image resizing info if applicable
            if self.resize_images_checkbox.isChecked():
                max_pixels = self.pixel_spinbox.value()
                report_lines.extend([
                    f"- Images resized to maximum {max_pixels}px on long side",
                    f"- Total images processed: {resized_images_count}"
                ])
            
            # Add user notes if provided
            if user_notes:
                report_lines.extend([
                    "",
                    "USER NOTES:",
                    "-" * 12,
                    user_notes
                ])
            
            # Write report file
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            
            self.emit_log(f"Archive report created: {report_path}")
            
        except Exception as e:
            self.emit_log(f"Could not create archive report: {str(e)}")

    def _resize_images_in_folder(self, folder_path, max_long_side):
        """Resize all images in a folder if their long side exceeds max_long_side"""
        if not HAS_PIL:
            self.emit_log("Pillow (PIL) is not installed — skipping image resizing. "
                         "Install with: pip install Pillow")
            return 0
        
        supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp')
        resized_count = 0
        
        try:
            image_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        image_files.append(os.path.join(root, file))
            
            if not image_files:
                return 0
                
            self.emit_log(f"Found {len(image_files)} images to potentially resize in {folder_path}")
            
            for i, image_path in enumerate(image_files):
                try:
                    # Update progress
                    self.progress_label.setText(f"Resizing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
                    
                    with Image.open(image_path) as img:
                        # Apply EXIF orientation to ensure correct rotation
                        img = ImageOps.exif_transpose(img)
                        
                        # Get original dimensions
                        width, height = img.size
                        long_side = max(width, height)
                        
                        # Only resize if long side exceeds the limit
                        if long_side > max_long_side:
                            # Calculate new dimensions maintaining aspect ratio
                            if width > height:
                                new_width = max_long_side
                                new_height = int(height * max_long_side / width)
                            else:
                                new_height = max_long_side
                                new_width = int(width * max_long_side / height)
                            
                            # Resize the image
                            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                            
                            # Save with appropriate quality settings
                            if image_path.lower().endswith(('.jpg', '.jpeg')):
                                resized_img.save(image_path, 'JPEG', quality=95, optimize=True)
                            else:
                                resized_img.save(image_path, optimize=True)
                            
                            resized_count += 1
                            self.emit_log(f"Resized {os.path.basename(image_path)} from {width}x{height} to {new_width}x{new_height}")
                        else:
                            # Even if not resizing, save with correct orientation if it's a JPEG
                            if image_path.lower().endswith(('.jpg', '.jpeg')):
                                img.save(image_path, 'JPEG', quality=95, optimize=True)
                            else:
                                img.save(image_path, optimize=True)
                
                except Exception as e:
                    self.emit_log(f"Could not resize {os.path.basename(image_path)}: {str(e)}")
                    continue
            
            return resized_count
            
        except Exception as e:
            self.emit_log(f"Error during image resizing: {str(e)}")
            return 0

    def _detect_remaining_absolute_paths(self, qgs_path):
        """Detect and report remaining absolute paths in the project file"""
        try:
            with open(str(qgs_path), 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_paths = {}
            
            # Look for Windows absolute paths
            windows_pattern = r'[A-Z]:[/\\][^"\s<>]*'
            for match in re.findall(windows_pattern, content):
                if self._is_likely_absolute_path(match):
                    path_type = self._categorize_path_simple(match)
                    if path_type not in found_paths:
                        found_paths[path_type] = set()
                    found_paths[path_type].add(match)
            
            # Look specifically for file:/// URIs
            file_uri_pattern = r'file:///[A-Z]:[/\\][^"\s<>]*'
            for match in re.findall(file_uri_pattern, content):
                if self._is_likely_absolute_path(match):
                    path_type = self._categorize_path_simple(match)
                    if path_type not in found_paths:
                        found_paths[path_type] = set()
                    found_paths[path_type].add(match)
            
            return found_paths
            
        except Exception as e:
            self.emit_log(f"Error detecting absolute paths: {str(e)}")
            return {}

    def _is_likely_absolute_path(self, path):
        """Check if a string is likely to be an absolute file path"""
        # Skip URLs, XML namespaces, and other non-path strings
        skip_patterns = [
            r'^https?://',
            r'^ftp://',
            r'xmlns',
            r'\.xsd$',
            r'\.dtd$',
            r'^qgis\.org',
            r'postgresql://',
            r'postgis:',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return False
        
        # Check if it looks like a file path
        return (
            len(path) > 3 and
            ('/' in path or '\\' in path) and
            not path.startswith('www.') and
            not path.endswith('.org') and
            not path.endswith('.com')
        )

    def _categorize_path_simple(self, path):
        """Categorize the type of absolute path found using simple string checks"""
        path_lower = path.lower()
        
        if '.csv' in path_lower:
            return 'CSV File References'
        elif any(ext in path_lower for ext in ['.svg', '.png', '.jpg', '.jpeg', '.tiff', '.pdf']):
            return 'Image/Document References'
        elif any(keyword in path_lower for keyword in ['browse', 'export', 'layout']):
            return 'UI Preferences/Directories'
        else:
            return 'Other File Paths'

    def _show_absolute_paths_summary(self, found_paths, output_folder):
        """Show a summary dialog of remaining absolute paths"""
        if not found_paths:
            return
        
        # Create summary message
        summary_parts = [
            "<h3>⚠️ Manual Review Required</h3>",
            "<p>The portable project was created successfully, but some absolute file paths remain that may need manual attention:</p>",
            ""
        ]
        
        total_paths = sum(len(paths) for paths in found_paths.values())
        
        for category, paths in found_paths.items():
            summary_parts.append(f"<h4>{category} ({len(paths)} path(s)):</h4>")
            summary_parts.append("<ul>")
            
            # Show first few paths as examples
            path_list = list(paths)[:3]  # Show max 3 examples
            for path in path_list:
                summary_parts.append(f"<li><code>{path}</code></li>")
            
            if len(paths) > 3:
                summary_parts.append(f"<li><i>... and {len(paths) - 3} more</i></li>")
            
            summary_parts.append("</ul>")
            summary_parts.append("")
        
        summary_parts.extend([
            "<h4>What you should do:</h4>",
            "<ul>",
            "<li><b>CSV files:</b> Copy the referenced CSV files to your project folder and update paths to be relative</li>",
            "<li><b>UI Preferences:</b> These are usually safe to ignore as they're user interface settings</li>",
            "<li><b>Images/Documents:</b> Copy referenced files to your project folder if needed</li>",
            "<li><b>Other paths:</b> Review and update as needed for your portable project</li>",
            "</ul>",
            "",
            f"<p><b>Tip:</b> You can search for absolute paths in your project file:<br>",
            f"<code>{os.path.basename(output_folder)}_portable.qgs</code></p>",
            "",
            f"<p><small>Total paths found: {total_paths}</small></p>"
        ])
        
        # Show dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Manual Review Required - Absolute Paths Found")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText("\n".join(summary_parts))
        msg.setIcon(MsgBoxIconWarning)
        msg.setStandardButtons(MsgBoxOk)
        msg.setDefaultButton(MsgBoxOk)
        
        # Make dialog larger
        msg.setMinimumWidth(600)
        msg.exec()

    def _try_convert_csv_paths_to_relative(self, qgs_path, output_folder):
        """Attempt to convert CSV file paths to relative paths if the files exist in the project"""
        try:
            with open(str(qgs_path), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use targeted pattern for CSV LayerSource entries
            csv_pattern = r'<Option name="LayerSource"[^>]*value="file:///([A-Z]:[/\\][^"]*\.csv[^"]*)"'
            csv_matches = re.findall(csv_pattern, content)
            
            if not csv_matches:
                return 0
            
            updated_content = content
            conversions_made = 0
            
            for csv_path in csv_matches:
                try:
                    # Extract just the filename
                    csv_filename = os.path.basename(csv_path.split('?')[0])  # Remove query parameters
                    
                    # Check if this CSV file exists in the output folder
                    potential_csv_path = Path(output_folder) / csv_filename
                    if potential_csv_path.exists():
                        # Create relative path
                        relative_path = f"./{csv_filename}"
                        query_part = ""
                        if '?' in csv_path:
                            query_part = "?" + csv_path.split('?', 1)[1]
                        
                        new_source = f"file:///{relative_path}{query_part}"
                        old_source = f"file:///{csv_path}"
                        
                        # Replace in content
                        updated_content = updated_content.replace(old_source, new_source)
                        conversions_made += 1
                        self.emit_log(f"Converted CSV path to relative: {csv_filename}")
                except Exception as e:
                    self.emit_log(f"Error processing CSV path {csv_path}: {str(e)}")
                    continue
            
            if conversions_made > 0:
                # Write updated content back
                with open(str(qgs_path), 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                self.emit_log(f"Successfully converted {conversions_made} CSV path(s) to relative")
            
            return conversions_made
            
        except Exception as e:
            self.emit_log(f"Error converting CSV paths: {str(e)}")
            return 0

    def _on_archive_project(self):
        output_folder = self.output_folder_edit.text().strip()
        if not self.validate_non_empty_field(output_folder, "output folder"):
            return
        if not os.path.isdir(output_folder):
            self.emit_log("Please select a valid output folder.")
            return

        project = QgsProject.instance()
        project_file = Path(project.fileName())
        if not project_file.exists():
            self.emit_log("No QGIS project is currently open.")
            return

        # Build warning message
        warning_parts = [
            "This will copy ALL files and folders from the project directory to the output folder.",
            "",
            "This includes:",
            "• DCIM folder (which might be quite large)",
            "• All other project files and folders",
            "• PostgreSQL layers will be converted to Geopackage",
            "• Database credentials will be automatically removed"
        ]
        
        # Add image resizing warning if enabled
        if self.resize_images_checkbox.isChecked():
            max_pixels = self.pixel_spinbox.value()
            warning_parts.extend([
                "",
                f"• Images will be resized to {max_pixels}px on the long side",
                "• This may take considerable time with many images"
            ])
        
        warning_parts.extend([
            "",
            "Do you want to continue?"
        ])
        
        warning_msg = "\n".join(warning_parts)
        
        if not self.confirm_action("Copy All Project Files", warning_msg):
            return

        # Start progress
        self.emit_progress_started()
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.archive_btn.setEnabled(False)

        project_name = os.path.splitext(os.path.basename(project_file))[0]
        export_qgs_filename = f"{project_name}_portable.qgs"
        export_path = Path(output_folder) / export_qgs_filename
        gpkg_path = Path(output_folder) / "data.gpkg"

        try:
            # Count total steps for progress calculation
            total_layers = len([layer for layer in project.mapLayers().values() 
                              if layer.type() == LayerTypeVector])
            project_dir = project_file.parent
            total_files = len([item for item in project_dir.iterdir() if item.name != project_file.name])
            
            total_steps = total_files + total_layers + 5  # +5 for project copy, final update, CSV conversion, path detection, and report creation
            current_step = 0
            
            # Switch to determinate progress
            self.progress_bar.setRange(0, total_steps)
            self.progress_label.setText("Copying project files...")

            # 1. Copy all files and folders from project directory to output folder (except the QGS file)
            original_qgs_name = project_file.name
            dcim_folders = []  # Track DCIM folders for potential resizing
            
            # Only copy if source and target directories are different
            if str(project_dir) != str(Path(output_folder)):
                self.emit_log(f"Copying files from project directory: {project_dir}")
                
                for item in project_dir.iterdir():
                    if item.name == original_qgs_name:
                        # Skip the original QGS file as we'll create the portable version
                        continue
                    
                    target_path = Path(output_folder) / item.name
                    
                    if item.is_file():
                        self.progress_label.setText(f"Copying file: {item.name}")
                        shutil.copy2(item, target_path)
                        self.emit_log(f"Copied file: {item.name}")
                    elif item.is_dir():
                        self.progress_label.setText(f"Copying folder: {item.name}")
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.copytree(item, target_path)
                        self.emit_log(f"Copied folder: {item.name}")
                        
                        # Track DCIM folders for potential resizing
                        if item.name.upper() == "DCIM":
                            dcim_folders.append(target_path)
                    
                    current_step += 1
                    self.progress_bar.setValue(current_step)
            else:
                self.emit_log("Source and target directories are the same, skipping file copy")
                # Still need to find DCIM folders in the current directory
                for item in project_dir.iterdir():
                    if item.is_dir() and item.name.upper() == "DCIM":
                        dcim_folders.append(item)
                current_step += total_files  # Skip file copy steps
                self.progress_bar.setValue(current_step)

            # 2. Resize images in DCIM folders if requested
            total_resized = 0
            if self.resize_images_checkbox.isChecked() and dcim_folders:
                max_pixels = self.pixel_spinbox.value()
                self.emit_log(f"Resizing images in DCIM folders to {max_pixels}px long side...")
                
                for dcim_folder in dcim_folders:
                    self.progress_label.setText(f"Processing images in {dcim_folder.name}...")
                    resized_count = self._resize_images_in_folder(str(dcim_folder), max_pixels)
                    total_resized += resized_count
                    self.emit_log(f"Resized {resized_count} images in {dcim_folder}")
                
                self.emit_log(f"Total images resized: {total_resized}")

            # 3. Copy the current project file to output folder
            self.progress_label.setText("Copying project file...")
            shutil.copy2(str(project_file), str(export_path))
            self.emit_log(f"Copied project file to: {export_path}")
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 4. Convert all layers to a single geopackage
            self.progress_label.setText("Converting layers to geopackage...")
            new_layer_sources = {}
            postgresql_layers = []
            first_layer = True
            
            for layer_id, layer in project.mapLayers().items():
                if layer.type() == LayerTypeVector:
                    # Check if it's a PostgreSQL layer
                    provider_type = layer.providerType()
                    source = layer.source()
                    
                    if provider_type == "postgres" or "postgresql" in source.lower():
                        postgresql_layers.append(layer)
                        self.emit_log(f"Found PostgreSQL layer: {layer.name()}")
                    
                    # Export layer to geopackage
                    layer_name = layer.name().replace(' ', '_').replace('/', '_')
                    self.progress_label.setText(f"Converting layer: {layer.name()}")
                    
                    # Create write options
                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.driverName = "GPKG"
                    options.fileEncoding = "utf-8"
                    options.layerName = layer_name
                    
                    # For the first layer, create/overwrite the geopackage
                    # For subsequent layers, append to existing geopackage
                    if first_layer:
                        options.actionOnExistingFile = CreateOrOverwriteFile
                        first_layer = False
                    else:
                        options.actionOnExistingFile = CreateOrOverwriteLayer
                    
                    # Export layer (V3 for QGIS ≥3.10.3 / 4.x, fallback for older)
                    if HAS_WRITE_V3:
                        error, error_message, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                            layer, 
                            str(gpkg_path),
                            QgsProject.instance().transformContext(),
                            options
                        )
                    else:
                        error, error_message = QgsVectorFileWriter.writeAsVectorFormat(
                            layer, 
                            str(gpkg_path),
                            options
                        )
                    
                    if error == WriterNoError:
                        # Use relative path since GeoPackage is always next to QGS file
                        new_source = f"data.gpkg|layername={layer_name}"
                        new_layer_sources[layer_id] = new_source
                        self.emit_log(f"Exported {layer.name()} to geopackage")
                    else:
                        self.emit_log(f"Failed to export {layer.name()}: {error_message}")
                    
                    current_step += 1
                    self.progress_bar.setValue(current_step)

            # 5. Update the copied project file to point to geopackage and clean credentials
            self.progress_label.setText("Updating project file...")
            if new_layer_sources:
                self._update_project_sources_comprehensive(export_path, new_layer_sources, postgresql_layers, str(gpkg_path))
                self.emit_log("Updated project file to use geopackage sources and removed credentials")
            
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 6. Try to convert CSV paths to relative if possible
            self.progress_label.setText("Converting CSV paths to relative...")
            csv_conversions = self._try_convert_csv_paths_to_relative(export_path, output_folder)
            if csv_conversions > 0:
                self.emit_log(f"Converted {csv_conversions} CSV paths to relative")
            
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 7. Detect remaining absolute paths and inform user
            self.progress_label.setText("Checking for remaining absolute paths...")
            remaining_paths = self._detect_remaining_absolute_paths(export_path)
            
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 8. Create archive report
            self.progress_label.setText("Creating archive report...")
            self._create_archive_report(
                str(output_folder), 
                str(project_file), 
                total_resized
            )
            current_step += 1
            self.progress_bar.setValue(current_step)

            self.progress_label.setText("Complete!")
            self.emit_log(f"✓ Successfully archived project '{project_name}' to {export_path}")
            
            # Show summary of remaining paths if any found
            if remaining_paths:
                self._show_absolute_paths_summary(remaining_paths, output_folder)
            else:
                self.emit_log("✓ No remaining absolute paths detected")
            
            self.project_archived.emit(str(export_path))
            
        except Exception as e:
            self.emit_log(f"Error creating archive: {str(e)}")
        finally:
            self.emit_progress_finished()
            self.progress_label.setVisible(False)
            self.progress_bar.setVisible(False)
            self.archive_btn.setEnabled(True)

    def _clean_credentials_from_content(self, content):
        """Clean database credentials from QGS content using similar logic as clean_qgs_tab.py"""
        changes_count = 0
        cleaned_content = content
        
        # Remove user credentials
        user_matches = re.findall(r'user=[\'"][^\'\"]*[\'"]|user=[^\s]+', cleaned_content)
        changes_count += len(user_matches)
        
        # Remove user credentials (being very careful about spaces)
        cleaned_content = re.sub(r'\s+user=[\'"][^\'\"]*[\'"]', '', cleaned_content)
        cleaned_content = re.sub(r'\s+user=[^\s]+', '', cleaned_content)
        cleaned_content = re.sub(r'user=[\'"][^\'\"]*[\'"]\s+', '', cleaned_content)
        cleaned_content = re.sub(r'user=[^\s]+\s+', '', cleaned_content)
        cleaned_content = re.sub(r'user=[\'"][^\'\"]*[\'"]', '', cleaned_content)
        cleaned_content = re.sub(r'user=[^\s]+', '', cleaned_content)
        
        # Remove password credentials
        password_matches = re.findall(r'password=[\'"][^\'\"]*[\'"]|password=[^\s]+', cleaned_content)
        changes_count += len(password_matches)
        
        # Remove password credentials (being very careful about spaces)
        cleaned_content = re.sub(r'\s+password=[\'"][^\'\"]*[\'"]', '', cleaned_content)
        cleaned_content = re.sub(r'\s+password=[^\s]+', '', cleaned_content)
        cleaned_content = re.sub(r'password=[\'"][^\'\"]*[\'"]\s+', '', cleaned_content)
        cleaned_content = re.sub(r'password=[^\s]+\s+', '', cleaned_content)
        cleaned_content = re.sub(r'password=[\'"][^\'\"]*[\'"]', '', cleaned_content)
        cleaned_content = re.sub(r'password=[^\s]+', '', cleaned_content)
        
        return cleaned_content, changes_count

    def _update_project_sources_comprehensive(self, qgs_path, new_sources, postgresql_layers, gpkg_path):
        """Comprehensive update of the project file to use geopackage sources and remove all PostgreSQL references"""
        try:
            # Read the file content
            with open(str(qgs_path), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean database credentials first
            content, creds_removed = self._clean_credentials_from_content(content)
            if creds_removed > 0:
                self.emit_log(f"Removed {creds_removed} database credential(s)")
            
            # Parse the XML
            root = ET.fromstring(content)
            
            # Create layer ID to layer name mapping for easier lookup
            layer_id_to_name = {}
            for layer_id, layer in QgsProject.instance().mapLayers().items():
                if layer_id in new_sources:
                    layer_name = layer.name().replace(' ', '_').replace('/', '_')
                    layer_id_to_name[layer_id] = layer_name
            
            # 1. Update basic maplayer elements
            maplayers = root.findall(".//maplayer")
            for maplayer in maplayers:
                layer_id = maplayer.get("id") or maplayer.findtext("id")
                
                if layer_id in new_sources:
                    # Update datasource
                    datasource_elem = maplayer.find("datasource")
                    if datasource_elem is not None:
                        datasource_elem.text = new_sources[layer_id]
                    
                    # Update provider to 'ogr' for geopackage
                    provider_elem = maplayer.find("provider")
                    if provider_elem is not None:
                        provider_elem.text = "ogr"
                    
                    self.emit_log(f"Updated maplayer {layer_id} source in project file")
            
            # 2. Update layer-tree-layer elements (providerKey and source attributes)
            layer_tree_layers = root.findall(".//layer-tree-layer")
            for layer_tree_layer in layer_tree_layers:
                layer_id = layer_tree_layer.get("id")
                
                if layer_id in new_sources:
                    # Update providerKey attribute
                    layer_tree_layer.set("providerKey", "ogr")
                    
                    # Update source attribute
                    layer_tree_layer.set("source", new_sources[layer_id])
                    
                    self.emit_log(f"Updated layer-tree-layer {layer_id} in project file")
            
            # 3. Update relation elements
            relations = root.findall(".//relation")
            for relation in relations:
                # Update referencingLayer dataSource
                referencing_layer = relation.get("referencingLayer")
                if referencing_layer in new_sources:
                    relation.set("dataSource", new_sources[referencing_layer])
                
                # Update referencedLayer dataSource  
                referenced_layer = relation.get("referencedLayer")
                if referenced_layer in new_sources:
                    relation.set("dataSource", new_sources[referenced_layer])
                
                # Update providerKey
                if referencing_layer in new_sources or referenced_layer in new_sources:
                    relation.set("providerKey", "ogr")
            
            # 4. Update Layer elements in project styles
            layer_elements = root.findall(".//Layer")
            for layer_elem in layer_elements:
                source = layer_elem.get("source")
                if source and ("postgres" in source.lower() or "dbname=" in source):
                    # Try to find matching layer by source pattern
                    for layer_id, new_source in new_sources.items():
                        # This is a simplified matching - you might want to improve this
                        if layer_id in source or any(part in source for part in source.split()):
                            layer_elem.set("source", new_source)
                            layer_elem.set("provider", "ogr")
                            break
            
            # 5. Update LayerStyle elements
            layer_styles = root.findall(".//LayerStyle")
            for layer_style in layer_styles:
                layer_id = layer_style.get("layerid")
                if layer_id in new_sources:
                    layer_style.set("source", new_sources[layer_id])
                    layer_style.set("provider", "ogr")
            
            # 6. Update Atlas configuration
            atlas = root.find(".//Atlas")
            if atlas is not None:
                coverage_layer = atlas.get("coverageLayer")
                if coverage_layer in new_sources:
                    atlas.set("coverageLayer", coverage_layer)
                    atlas.set("coverageLayerSource", new_sources[coverage_layer])
                    atlas.set("coverageLayerProvider", "ogr")
            
            # 7. Update GPS settings
            gps_settings = root.find(".//ProjectGpsSettings")
            if gps_settings is not None:
                dest_layer = gps_settings.get("destinationLayer")
                if dest_layer in new_sources:
                    gps_settings.set("destinationLayerSource", new_sources[dest_layer])
                    gps_settings.set("destinationLayerProvider", "ogr")
            
            # 8. Update Option elements with LayerProviderName
            option_elements = root.findall(".//Option[@name='LayerProviderName']")
            for option_elem in option_elements:
                if option_elem.get("value") == "postgres":
                    option_elem.set("value", "ogr")
            
            # 9. Clean up any remaining PostgreSQL references in the serialized content
            content = ET.tostring(root, encoding='unicode')
            
            # Additional text-based cleanup for any missed references
            # Replace remaining postgres provider references
            content = re.sub(r'providerKey="postgres"', 'providerKey="ogr"', content)
            content = re.sub(r"providerKey='postgres'", "providerKey='ogr'", content)
            content = re.sub(r'provider="postgres"', 'provider="ogr"', content)
            content = re.sub(r"provider='postgres'", "provider='ogr'", content)
            
            # Replace LayerProviderName values
            content = re.sub(r'<Option name="LayerProviderName" type="QString" value="postgres" />',
                           '<Option name="LayerProviderName" type="QString" value="ogr" />', content)
            
            # Write the updated XML back to file
            with open(str(qgs_path), 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(content)
            
            self.emit_log("Comprehensive project file update completed")
            
        except Exception as e:
            self.emit_log(f"Error updating project file: {str(e)}")

    def _set_default_output_folder(self):
        documents = os.path.expanduser("~/Documents")
        self.output_folder_edit.setText(documents if os.path.isdir(documents) else os.getcwd())

    def get_output_folder(self):
        return self.output_folder_edit.text().strip()

    def set_output_folder(self, folder_path):
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            self.output_folder_edit.setText(folder_path)
            return True
        return False