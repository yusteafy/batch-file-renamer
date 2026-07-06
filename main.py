import sys
import os
import re
import shutil
import random
import json
from typing import List, Tuple
from datetime import datetime
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog, QLineEdit, QLabel, QSpinBox, QCheckBox, QMessageBox, QGroupBox, QDialog, QListWidget, QRadioButton, QSplitter, QToolButton, QStackedWidget, QComboBox

META_TAGS = [
    "{File_Size}", "{File_SizeBytes}", "{File_SizeKB}", "{File_SizeMB}", "{File_SizeGB}",
    "{Date_Now}", "{Date_Now_YMD}", "{Date_Now_Y-M-D}", "{Date_Now_YMmD}",
    "{Date_Now_Year}", "{Date_Now_Month}", "{Date_Now_Day}",
    "{Time_Now_HMS}", "{Time_Now_H:M:S}", "{Time_Now_H}", "{Time_Now_M}", "{Time_Now_S}",
    "{File_DateCreated}", "{File_DateCreated_YMD}", "{File_DateCreated_Y-M-D}", "{File_DateCreated_YMmD}",
    "{File_DateModified}", "{File_DateModified_YMD}", "{File_DateModified_Y-M-D}", "{File_DateModified_YMmD}",
    "{File_FilePath}", "{File_FileName}", "{File_Extension}", "{File_FolderName}", "{File_FolderPath}"
]

class RenameWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, operations: List[Tuple[str, str]]):
        super().__init__()
        self.operations = operations

    def run(self):
        try:
            for old_path, new_path in self.operations:
                if os.path.exists(old_path):
                    shutil.move(old_path, new_path)
            self.finished.emit(True, "Renamed successfully!")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

class ClickableRulePlaceholder(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)

class DragDropPlaceholder(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            paths = [url.toLocalFile() for url in urls]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

class DragDropTable(QTableWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            paths = [url.toLocalFile() for url in urls]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_rows()
        else:
            super().keyPressEvent(event)

    def delete_selected_rows(self):
        pass

class AddRuleDialog(QDialog):
    AVAILABLE_RULES = ["Insert", "Delete", "Replace", "Strip", "Case", "Serialize", "Randomize", "Padding", "Clean Up"]

    def __init__(self, parent=None, rule_config=None):
        super().__init__(parent)
        self.setWindowTitle("Add Rule" if rule_config is None else "Edit Rule")
        self.selected_rule = None
        self.rule_config = {}
        self.edit_mode = rule_config is not None
        self.existing_rule_config = rule_config if rule_config else {}
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Select a rule:"))

        self.rule_list = QListWidget()
        for rule in self.AVAILABLE_RULES:
            self.rule_list.addItem(rule)
        self.rule_list.itemClicked.connect(self.on_rule_clicked)

        left_layout.addWidget(self.rule_list)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(200)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Configuration:"))

        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout()
        self.config_widget.setLayout(self.config_layout)

        right_layout.addWidget(self.config_widget)

        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Rule" if not self.edit_mode else "Update Rule")
        self.add_btn.clicked.connect(self.on_add_rule)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(close_btn)

        right_layout.addLayout(button_layout)

        main_layout.addWidget(left_widget)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        if self.edit_mode and self.existing_rule_config:
            rule_name = self.existing_rule_config.get("name")
            for i in range(self.rule_list.count()):
                if self.rule_list.item(i).text() == rule_name:
                    self.rule_list.setCurrentRow(i)
                    self.on_rule_clicked(self.rule_list.item(i))
                    self.load_rule_config()
                    break
        else:
            self.rule_list.setCurrentRow(0)
            self.on_rule_clicked(self.rule_list.item(0))

    def on_rule_clicked(self, item):
        rule_name = item.text()
        self.selected_rule = rule_name
        self.clear_layout_items(self.config_layout)

        rule_configs = {
            "Insert": self.show_insert_config,
            "Delete": self.show_delete_config,
            "Replace": self.show_replace_config,
            "Strip": self.show_strip_config,
            "Case": self.show_case_config,
            "Serialize": self.show_serialize_config,
            "Randomize": self.show_randomize_config,
            "Padding": self.show_padding_config,
            "Clean Up": self.show_clean_up_config
        }

        if rule_name in rule_configs:
            rule_configs[rule_name]()
        else:
            self.config_layout.addWidget(QLabel(f"Configuration for {rule_name}"))

        self.config_layout.addStretch()

    def on_add_rule(self):
        self.rule_config = self._extract_rule_values()

        if self.rule_config is None:
            return

        self.accept()

    def clear_layout_items(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout_items(item.layout())

    def load_rule_config(self):
        if not self.edit_mode or not self.existing_rule_config:
            return

        rule_name = self.existing_rule_config.get("name")

        if rule_name == "Insert":
            self.insert_text.setText(self.existing_rule_config.get("text", ""))
            self.insert_meta_tag.setChecked(self.existing_rule_config.get("meta_tag", False))
            self.insert_meta_tag_list.setVisible(self.insert_meta_tag.isChecked())
            self.insert_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))
            self.right_to_left.setChecked(self.existing_rule_config.get("right_to_left", False))

            where = self.existing_rule_config.get("where", "Prefix")
            if where == "Prefix":
                self.where_prefix.setChecked(True)
            elif where == "Suffix":
                self.where_suffix.setChecked(True)
            elif where.startswith("Position:"):
                self.where_position.setChecked(True)
                pos = int(where.split(":")[1])
                self.where_position_value.setValue(pos)
            elif where.startswith("After text:"):
                self.where_after_text.setChecked(True)
                text = where.split(":", 1)[1]
                self.where_after_text_value.setText(text)
            elif where.startswith("Before text:"):
                self.where_before_text.setChecked(True)
                text = where.split(":", 1)[1]
                self.where_before_text_value.setText(text)
            elif where == "Replace current name":
                self.where_replace.setChecked(True)

        elif rule_name == "Delete":
            from_type = self.existing_rule_config.get("from_type", "Position")
            from_value = self.existing_rule_config.get("from_value", 1)
            until_type = self.existing_rule_config.get("until_type", "Count")
            until_value = self.existing_rule_config.get("until_value", 1)

            if from_type == "Position":
                self.delete_from_position.setChecked(True)
                self.delete_from_position_value.setValue(from_value)
            else:
                self.delete_from_delimiter.setChecked(True)
                self.delete_from_delimiter_value.setText(str(from_value))

            if until_type == "Till the end":
                self.delete_until_till_end.setChecked(True)
            elif until_type == "Count":
                self.delete_until_count.setChecked(True)
                self.delete_until_count_value.setValue(until_value)
            else:
                self.delete_until_delimiter.setChecked(True)
                self.delete_until_delimiter_value.setText(str(until_value))

            self.delete_current_name.setChecked(self.existing_rule_config.get("delete_current_name", False))
            self.delete_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))
            self.delete_right_to_left.setChecked(self.existing_rule_config.get("right_to_left", False))
            self.delete_do_not_remove_delimiters.setChecked(self.existing_rule_config.get("do_not_remove_delimiters", False))
            self.on_delete_current_name_toggled()

        elif rule_name == "Replace":
            self.replace_find.setText(self.existing_rule_config.get("find", ""))
            self.replace_replace.setText(self.existing_rule_config.get("replace", ""))
            self.replace_case_sensitive.setChecked(self.existing_rule_config.get("case_sensitive", False))
            self.replace_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

            occurrences = self.existing_rule_config.get("occurrences", "All")
            if occurrences == "All":
                self.replace_all.setChecked(True)
            elif occurrences == "First":
                self.replace_first.setChecked(True)
            else:
                self.replace_last.setChecked(True)

        elif rule_name == "Strip":
            chars = self.existing_rule_config.get("characters", "")
            if "a" in chars:
                self.strip_english.setChecked(True)
            if "0" in chars:
                self.strip_digits.setChecked(True)
            if "!" in chars or "@" in chars:
                self.strip_symbols.setChecked(True)
            if "{" in chars or "[" in chars:
                self.strip_brackets.setChecked(True)

            user_chars = ""
            base_chars = ""
            if self.strip_english.isChecked():
                base_chars += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if self.strip_digits.isChecked():
                base_chars += "0123456789"
            if self.strip_symbols.isChecked():
                base_chars += "!@#$%^&~-+=~.,"
            if self.strip_brackets.isChecked():
                base_chars += "(){}[]"

            for char in chars:
                if char not in base_chars:
                    user_chars += char

            if user_chars:
                self.strip_user.setChecked(True)
                self.strip_user_input.setText(user_chars)

            self.strip_invert.setChecked(self.existing_rule_config.get("invert", False))
            self.strip_case_sensitive.setChecked(self.existing_rule_config.get("case_sensitive", False))
            self.strip_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

        elif rule_name == "Case":
            case_type = self.existing_rule_config.get("case_type", "Capitalize Every Word")

            if case_type == "Capitalize Every Word":
                self.case_capitalize_every_word.setChecked(True)
            elif case_type == "Capitalize AND Preserve":
                self.case_capitalize_and_preserve.setChecked(True)
            elif case_type == "all lower case":
                self.case_all_lower.setChecked(True)
            elif case_type == "ALL UPPER CASE":
                self.case_all_upper.setChecked(True)
            elif case_type == "iNVeRT cASE":
                self.case_invert.setChecked(True)
            else:
                self.case_first_letter.setChecked(True)

            self.case_ext_always_lower.setChecked(self.existing_rule_config.get("ext_always_lower", False))
            self.case_ext_always_upper.setChecked(self.existing_rule_config.get("ext_always_upper", False))
            self.case_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

        elif rule_name == "Serialize":
            self.serialize_index_starts.setValue(self.existing_rule_config.get("index_starts", 1))
            self.serialize_repeat.setValue(self.existing_rule_config.get("repeat", 1))
            self.serialize_step.setValue(self.existing_rule_config.get("step", 1))

            reset_every = self.existing_rule_config.get("reset_every")
            if reset_every is not None:
                self.serialize_reset_every_check.setChecked(True)
                self.serialize_reset_every.setValue(reset_every)

            self.serialize_reset_if_folder_changes.setChecked(self.existing_rule_config.get("reset_if_folder_changes", False))

            self.serialize_pad_check.setChecked(self.existing_rule_config.get("pad_with_zeros", True))
            self.serialize_pad_length.setValue(self.existing_rule_config.get("pad_length", 1))

            numbering = self.existing_rule_config.get("numbering_system", "Decimal digits (0,9)")
            index = self.serialize_numbering_system.findText(numbering)
            if index >= 0:
                self.serialize_numbering_system.setCurrentIndex(index)

            where = self.existing_rule_config.get("where", "Prefix")
            if where == "Prefix":
                self.serialize_where_prefix.setChecked(True)
            elif where == "Suffix":
                self.serialize_where_suffix.setChecked(True)
            elif where.startswith("Position:"):
                self.serialize_where_position.setChecked(True)
                pos = int(where.split(":")[1])
                self.serialize_where_position_value.setValue(pos)
            else:
                self.serialize_where_replace.setChecked(True)

            self.serialize_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

        elif rule_name == "Randomize":
            self.randomize_length.setValue(self.existing_rule_config.get("length", 1))
            chars = self.existing_rule_config.get("characters", "")

            if "0" in chars:
                self.randomize_digits.setChecked(True)
            if "a" in chars:
                self.randomize_english.setChecked(True)

            base_chars = ""
            if self.randomize_digits.isChecked():
                base_chars += "0123456789"
            if self.randomize_english.isChecked():
                base_chars += "abcdefghijklmnopqrstuvwxyz"

            user_chars = ""
            for char in chars:
                if char not in base_chars:
                    user_chars += char

            if user_chars:
                self.randomize_user.setChecked(True)
                self.randomize_user_input.setText(user_chars)

            where = self.existing_rule_config.get("where", "Prefix")
            if where == "Prefix":
                self.randomize_where_prefix.setChecked(True)
            elif where == "Suffix":
                self.randomize_where_suffix.setChecked(True)
            elif where.startswith("Position:"):
                self.randomize_where_position.setChecked(True)
                pos = int(where.split(":")[1])
                self.randomize_where_position_value.setValue(pos)
            else:
                self.randomize_where_replace.setChecked(True)

            self.randomize_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

        elif rule_name == "Padding":
            self.padding_add_check.setChecked(self.existing_rule_config.get("add_padding", False))
            self.padding_add_length.setValue(self.existing_rule_config.get("add_length", 1))
            self.padding_add_length.setEnabled(self.padding_add_check.isChecked())

            self.padding_remove_check.setChecked(self.existing_rule_config.get("remove_padding", False))

            which = self.existing_rule_config.get("which", "All")
            if which == "First":
                self.padding_which_first.setChecked(True)
            elif which == "Last":
                self.padding_which_last.setChecked(True)
            else:
                self.padding_which_all.setChecked(True)

            self.padding_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

        elif rule_name == "Clean Up":
            self.cleanup_brackets_round.setChecked(self.existing_rule_config.get("strip_round_brackets", False))
            self.cleanup_brackets_square.setChecked(self.existing_rule_config.get("strip_square_brackets", False))
            self.cleanup_brackets_curly.setChecked(self.existing_rule_config.get("strip_curly_brackets", False))

            self.cleanup_replace_dot.setChecked(self.existing_rule_config.get("replace_dot", False))
            self.cleanup_replace_comma.setChecked(self.existing_rule_config.get("replace_comma", False))
            self.cleanup_replace_underscore.setChecked(self.existing_rule_config.get("replace_underscore", False))
            self.cleanup_replace_dash.setChecked(self.existing_rule_config.get("replace_dash", False))
            self.cleanup_replace_percent20.setChecked(self.existing_rule_config.get("replace_percent20", False))

            self.cleanup_skip_number_sequences.setChecked(self.existing_rule_config.get("skip_number_sequences", False))
            self.cleanup_camel_case.setChecked(self.existing_rule_config.get("camel_case_split", False))
            self.cleanup_fix_spaces.setChecked(self.existing_rule_config.get("fix_spaces", True))
            self.cleanup_normalize_unicode.setChecked(self.existing_rule_config.get("normalize_unicode_spaces", True))
            self.cleanup_strip_unicode_marks.setChecked(self.existing_rule_config.get("strip_unicode_marks", False))
            self.cleanup_skip_extension.setChecked(self.existing_rule_config.get("skip_extension", True))

    def show_insert_config(self):
        insert_layout = QHBoxLayout()
        insert_layout.addWidget(QLabel("Insert:"))
        self.insert_text = QLineEdit()
        self.insert_text.setPlaceholderText("Text to insert")
        insert_layout.addWidget(self.insert_text)
        self.config_layout.addLayout(insert_layout)

        self.insert_meta_tag = QCheckBox("Add Meta Tag")
        self.insert_meta_tag.stateChanged.connect(self.on_insert_meta_tag_toggled)
        self.config_layout.addWidget(self.insert_meta_tag)

        self.insert_meta_tag_list = QListWidget()
        self.insert_meta_tag_list.setVisible(False)
        self.insert_meta_tag_list.setMinimumHeight(200)
        for tag in META_TAGS:
            self.insert_meta_tag_list.addItem(tag)
        self.insert_meta_tag_list.itemDoubleClicked.connect(self.on_insert_meta_tag_selected)
        self.config_layout.addWidget(self.insert_meta_tag_list)

        where_group = QGroupBox("Where:")
        where_layout = QVBoxLayout()

        self.where_prefix = QRadioButton("Prefix")
        self.where_prefix.setChecked(True)
        self.where_suffix = QRadioButton("Suffix")
        self.where_position = QRadioButton("Position:")
        self.where_position_value = QSpinBox()
        self.where_position_value.setValue(1)
        self.where_position_value.setEnabled(False)
        self.where_position.toggled.connect(self.where_position_value.setEnabled)

        self.right_to_left = QCheckBox("Right-to-left")
        self.right_to_left.setEnabled(False)
        self.where_position.toggled.connect(self.right_to_left.setEnabled)

        self.where_after_text = QRadioButton("After text:")
        self.where_after_text_value = QLineEdit()
        self.where_after_text_value.setEnabled(False)
        self.where_after_text.toggled.connect(self.where_after_text_value.setEnabled)

        self.where_before_text = QRadioButton("Before text:")
        self.where_before_text_value = QLineEdit()
        self.where_before_text_value.setEnabled(False)
        self.where_before_text.toggled.connect(self.where_before_text_value.setEnabled)

        where_layout.addWidget(self.where_prefix)
        where_layout.addWidget(self.where_suffix)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.where_position)
        pos_layout.addWidget(self.where_position_value)
        pos_layout.addWidget(self.right_to_left)
        pos_layout.addStretch()
        where_layout.addLayout(pos_layout)

        after_layout = QHBoxLayout()
        after_layout.addWidget(self.where_after_text)
        after_layout.addWidget(self.where_after_text_value)
        where_layout.addLayout(after_layout)

        before_layout = QHBoxLayout()
        before_layout.addWidget(self.where_before_text)
        before_layout.addWidget(self.where_before_text_value)
        where_layout.addLayout(before_layout)

        self.where_replace = QRadioButton("Replace current name")
        where_layout.addWidget(self.where_replace)

        where_group.setLayout(where_layout)
        self.config_layout.addWidget(where_group)

        self.insert_skip_extension = QCheckBox("Skip extension")
        self.insert_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.insert_skip_extension)

    def show_delete_config(self):
        from_group = QGroupBox("From:")
        from_layout = QVBoxLayout()

        self.delete_from_position = QRadioButton("Position:")
        self.delete_from_position.setChecked(True)
        self.delete_from_position_value = QSpinBox()
        self.delete_from_position_value.setValue(1)
        self.delete_from_position.toggled.connect(self.delete_from_position_value.setEnabled)

        self.delete_from_delimiter = QRadioButton("Delimiter:")
        self.delete_from_delimiter_value = QLineEdit()
        self.delete_from_delimiter_value.setEnabled(False)
        self.delete_from_delimiter.toggled.connect(self.delete_from_delimiter_value.setEnabled)

        from_pos_layout = QHBoxLayout()
        from_pos_layout.addWidget(self.delete_from_position)
        from_pos_layout.addWidget(self.delete_from_position_value)
        from_pos_layout.addStretch()
        from_layout.addLayout(from_pos_layout)

        from_delim_layout = QHBoxLayout()
        from_delim_layout.addWidget(self.delete_from_delimiter)
        from_delim_layout.addWidget(self.delete_from_delimiter_value)
        from_delim_layout.addStretch()
        from_layout.addLayout(from_delim_layout)

        from_group.setLayout(from_layout)
        self.delete_from_group = from_group
        self.config_layout.addWidget(from_group)

        until_group = QGroupBox("Until:")
        until_layout = QVBoxLayout()

        self.delete_until_count = QRadioButton("Count:")
        self.delete_until_count.setChecked(True)
        self.delete_until_count_value = QSpinBox()
        self.delete_until_count_value.setValue(1)
        self.delete_until_count.toggled.connect(self.delete_until_count_value.setEnabled)

        self.delete_until_delimiter = QRadioButton("Delimiter:")
        self.delete_until_delimiter_value = QLineEdit()
        self.delete_until_delimiter_value.setEnabled(False)
        self.delete_until_delimiter.toggled.connect(self.delete_until_delimiter_value.setEnabled)

        self.delete_until_till_end = QRadioButton("Till the end")

        until_count_layout = QHBoxLayout()
        until_count_layout.addWidget(self.delete_until_count)
        until_count_layout.addWidget(self.delete_until_count_value)
        until_count_layout.addStretch()
        until_layout.addLayout(until_count_layout)

        until_delim_layout = QHBoxLayout()
        until_delim_layout.addWidget(self.delete_until_delimiter)
        until_delim_layout.addWidget(self.delete_until_delimiter_value)
        until_delim_layout.addStretch()
        until_layout.addLayout(until_delim_layout)

        until_layout.addWidget(self.delete_until_till_end)
        until_group.setLayout(until_layout)
        self.delete_until_group = until_group
        self.config_layout.addWidget(until_group)

        self.delete_current_name = QCheckBox("Delete current name")
        self.delete_current_name.stateChanged.connect(self.on_delete_current_name_toggled)
        self.config_layout.addWidget(self.delete_current_name)

        self.delete_skip_extension = QCheckBox("Skip extension")
        self.delete_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.delete_skip_extension)

        self.delete_right_to_left = QCheckBox("Right-to-left")
        self.delete_right_to_left.setEnabled(True)
        self.config_layout.addWidget(self.delete_right_to_left)

        self.delete_skip_extension.stateChanged.connect(self.delete_right_to_left.setEnabled)

        self.delete_do_not_remove_delimiters = QCheckBox("Do not remove delimiters")
        self.config_layout.addWidget(self.delete_do_not_remove_delimiters)

    def show_replace_config(self):
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.replace_find = QLineEdit()
        self.replace_find.setPlaceholderText("Text to find")
        find_layout.addWidget(self.replace_find)
        self.config_layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_replace = QLineEdit()
        self.replace_replace.setPlaceholderText("Text to replace with")
        replace_layout.addWidget(self.replace_replace)
        self.config_layout.addLayout(replace_layout)

        self.replace_meta_tag = QCheckBox("Add Meta Tag")
        self.replace_meta_tag.stateChanged.connect(self.on_replace_meta_tag_toggled)
        self.config_layout.addWidget(self.replace_meta_tag)

        self.replace_meta_tag_list = QListWidget()
        self.replace_meta_tag_list.setVisible(False)
        self.replace_meta_tag_list.setMinimumHeight(200)
        for tag in META_TAGS:
            self.replace_meta_tag_list.addItem(tag)
        self.replace_meta_tag_list.itemDoubleClicked.connect(self.on_replace_meta_tag_selected)
        self.config_layout.addWidget(self.replace_meta_tag_list)

        occurrences_layout = QVBoxLayout()
        occurrences_layout.addWidget(QLabel("Occurrences:"))

        occurrences_radio_layout = QHBoxLayout()
        self.replace_all = QRadioButton("All")
        self.replace_all.setChecked(True)
        self.replace_first = QRadioButton("First")
        self.replace_last = QRadioButton("Last")

        occurrences_radio_layout.addWidget(self.replace_all)
        occurrences_radio_layout.addWidget(self.replace_first)
        occurrences_radio_layout.addWidget(self.replace_last)
        occurrences_radio_layout.addStretch()
        occurrences_layout.addLayout(occurrences_radio_layout)
        self.config_layout.addLayout(occurrences_layout)

        self.replace_case_sensitive = QCheckBox("Case sensitive")
        self.replace_case_sensitive.setChecked(False)
        self.config_layout.addWidget(self.replace_case_sensitive)

        self.replace_skip_extension = QCheckBox("Skip extension")
        self.replace_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.replace_skip_extension)

    def show_strip_config(self):
        config_group = QGroupBox("Configuration")
        config_group_layout = QVBoxLayout()

        char_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.strip_english = QCheckBox()
        english_label = QLineEdit("abcdefghijklmnopqrstuvwxyz")
        english_label.setReadOnly(True)
        row1.addWidget(QLabel("English:"))
        row1.addWidget(english_label)
        row1.addWidget(self.strip_english)
        char_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.strip_digits = QCheckBox()
        digits_label = QLineEdit("1234567890")
        digits_label.setReadOnly(True)
        row2.addWidget(QLabel("Digits:"))
        row2.addWidget(digits_label)
        row2.addWidget(self.strip_digits)
        char_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.strip_symbols = QCheckBox()
        symbols_label = QLineEdit("!@#$%^&~-+=~.,")
        symbols_label.setReadOnly(True)
        row3.addWidget(QLabel("Symbols:"))
        row3.addWidget(symbols_label)
        row3.addWidget(self.strip_symbols)
        char_layout.addLayout(row3)

        row4 = QHBoxLayout()
        self.strip_brackets = QCheckBox()
        brackets_label = QLineEdit("(){}[]")
        brackets_label.setReadOnly(True)
        row4.addWidget(QLabel("Brackets:"))
        row4.addWidget(brackets_label)
        row4.addWidget(self.strip_brackets)
        char_layout.addLayout(row4)

        row5 = QHBoxLayout()
        self.strip_user = QCheckBox()
        self.strip_user_input = QLineEdit()
        self.strip_user_input.setPlaceholderText("Enter custom characters")
        row5.addWidget(QLabel("User defined:"))
        row5.addWidget(self.strip_user_input)
        row5.addWidget(self.strip_user)
        char_layout.addLayout(row5)

        config_group_layout.addLayout(char_layout)
        config_group.setLayout(config_group_layout)
        self.config_layout.addWidget(config_group)

        self.strip_invert = QCheckBox("Strip all characters except selected")
        self.config_layout.addWidget(self.strip_invert)

        self.strip_case_sensitive = QCheckBox("Case sensitive")
        self.config_layout.addWidget(self.strip_case_sensitive)

        self.strip_skip_extension = QCheckBox("Skip extension")
        self.strip_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.strip_skip_extension)

    def show_case_config(self):
        config_group = QGroupBox("Case Change Configuration")
        config_group_layout = QVBoxLayout()

        case_layout = QVBoxLayout()

        self.case_capitalize_every_word = QRadioButton("Capitalize Every Word")
        self.case_capitalize_every_word.setChecked(True)
        case_layout.addWidget(self.case_capitalize_every_word)

        self.case_capitalize_and_preserve = QRadioButton("Capitalize AND Preserve")
        case_layout.addWidget(self.case_capitalize_and_preserve)

        self.case_all_lower = QRadioButton("all lower case")
        case_layout.addWidget(self.case_all_lower)

        self.case_all_upper = QRadioButton("ALL UPPER CASE")
        case_layout.addWidget(self.case_all_upper)

        self.case_invert = QRadioButton("iNVeRT cASE")
        case_layout.addWidget(self.case_invert)

        self.case_first_letter = QRadioButton("First letter capital")
        case_layout.addWidget(self.case_first_letter)

        config_group_layout.addLayout(case_layout)
        config_group.setLayout(config_group_layout)
        self.config_layout.addWidget(config_group)

        self.case_skip_extension = QCheckBox("Skip extension")
        self.case_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.case_skip_extension)

        self.case_ext_always_lower = QCheckBox("Extension always lower case")
        self.case_ext_always_lower.stateChanged.connect(self.on_case_ext_lower_toggled)
        self.config_layout.addWidget(self.case_ext_always_lower)

        self.case_ext_always_upper = QCheckBox("Extension always upper case")
        self.case_ext_always_upper.stateChanged.connect(self.on_case_ext_upper_toggled)
        self.config_layout.addWidget(self.case_ext_always_upper)

    def show_serialize_config(self):
        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()

        index_layout = QHBoxLayout()
        index_layout.addWidget(QLabel("Index starts:"))
        self.serialize_index_starts = QSpinBox()
        self.serialize_index_starts.setValue(1)
        self.serialize_index_starts.setMinimum(0)
        index_layout.addWidget(self.serialize_index_starts)
        index_layout.addStretch()
        left_layout.addLayout(index_layout)

        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat:"))
        self.serialize_repeat = QSpinBox()
        self.serialize_repeat.setValue(1)
        self.serialize_repeat.setMinimum(1)
        repeat_layout.addWidget(self.serialize_repeat)
        repeat_layout.addStretch()
        left_layout.addLayout(repeat_layout)

        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step:"))
        self.serialize_step = QSpinBox()
        self.serialize_step.setValue(1)
        self.serialize_step.setMinimum(1)
        step_layout.addWidget(self.serialize_step)
        step_layout.addStretch()
        left_layout.addLayout(step_layout)

        reset_every_layout = QHBoxLayout()
        self.serialize_reset_every_check = QCheckBox("Reset every:")
        self.serialize_reset_every = QSpinBox()
        self.serialize_reset_every.setValue(1)
        self.serialize_reset_every.setMinimum(1)
        self.serialize_reset_every.setEnabled(False)
        self.serialize_reset_every_check.stateChanged.connect(self.serialize_reset_every.setEnabled)
        reset_every_layout.addWidget(self.serialize_reset_every_check)
        reset_every_layout.addWidget(self.serialize_reset_every)
        reset_every_layout.addStretch()
        left_layout.addLayout(reset_every_layout)

        self.serialize_reset_if_folder_changes = QCheckBox("Reset if folder changes")
        left_layout.addWidget(self.serialize_reset_if_folder_changes)

        pad_layout = QHBoxLayout()
        self.serialize_pad_check = QCheckBox("Pad with zeros to length:")
        self.serialize_pad_length = QSpinBox()
        self.serialize_pad_length.setValue(1)
        self.serialize_pad_length.setMinimum(1)
        self.serialize_pad_length.setEnabled(True)
        self.serialize_pad_check.setChecked(True)
        self.serialize_pad_check.stateChanged.connect(self.serialize_pad_length.setEnabled)
        pad_layout.addWidget(self.serialize_pad_check)
        pad_layout.addWidget(self.serialize_pad_length)
        pad_layout.addStretch()
        left_layout.addLayout(pad_layout)

        numbering_layout = QHBoxLayout()
        numbering_layout.addWidget(QLabel("Numbering system:"))
        self.serialize_numbering_system = QComboBox()
        self.serialize_numbering_system.addItems([
            "Decimal digits (0,9)",
            "Lowercase letters (a-z)",
            "Uppercase letters (A-Z)",
            "Lowercase Roman (i,ii,iii...)",
            "Uppercase Roman (I,II,III...)"
        ])
        numbering_layout.addWidget(self.serialize_numbering_system)
        numbering_layout.addStretch()
        left_layout.addLayout(numbering_layout)

        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Insert where:"))

        self.serialize_where_prefix = QRadioButton("Prefix")
        self.serialize_where_prefix.setChecked(True)
        right_layout.addWidget(self.serialize_where_prefix)

        self.serialize_where_suffix = QRadioButton("Suffix")
        right_layout.addWidget(self.serialize_where_suffix)

        position_layout = QHBoxLayout()
        self.serialize_where_position = QRadioButton("Position:")
        self.serialize_where_position_value = QSpinBox()
        self.serialize_where_position_value.setValue(1)
        self.serialize_where_position_value.setEnabled(False)
        self.serialize_where_position.toggled.connect(self.serialize_where_position_value.setEnabled)
        position_layout.addWidget(self.serialize_where_position)
        position_layout.addWidget(self.serialize_where_position_value)
        position_layout.addStretch()
        right_layout.addLayout(position_layout)

        self.serialize_where_replace = QRadioButton("Replace current name")
        right_layout.addWidget(self.serialize_where_replace)

        self.serialize_skip_extension = QCheckBox("Skip extension")
        self.serialize_skip_extension.setChecked(True)
        right_layout.addWidget(self.serialize_skip_extension)

        right_layout.addStretch()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.config_layout.addWidget(container)

    def show_randomize_config(self):
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length of random sequence:"))
        self.randomize_length = QSpinBox()
        self.randomize_length.setValue(1)
        self.randomize_length.setMinimum(1)
        length_layout.addWidget(self.randomize_length)
        length_layout.addStretch()
        self.config_layout.addLayout(length_layout)

        self.randomize_digits = QCheckBox()
        self.randomize_digits.setChecked(True)
        digits_label = QLineEdit("0123456789")
        digits_label.setReadOnly(True)
        digits_layout = QHBoxLayout()
        digits_layout.addWidget(QLabel("Digits:"))
        digits_layout.addWidget(digits_label)
        digits_layout.addWidget(self.randomize_digits)
        self.config_layout.addLayout(digits_layout)

        self.randomize_english = QCheckBox()
        english_label = QLineEdit("abcdefghijklmnopqrstuvwxyz")
        english_label.setReadOnly(True)
        english_layout = QHBoxLayout()
        english_layout.addWidget(QLabel("English (a-z):"))
        english_layout.addWidget(english_label)
        english_layout.addWidget(self.randomize_english)
        self.config_layout.addLayout(english_layout)

        self.randomize_user = QCheckBox()
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User defined:"))
        self.randomize_user_input = QLineEdit()
        self.randomize_user_input.setPlaceholderText("Enter custom characters")
        self.randomize_user_input.setEnabled(False)
        self.randomize_user.toggled.connect(self.randomize_user_input.setEnabled)
        user_layout.addWidget(self.randomize_user_input)
        user_layout.addWidget(self.randomize_user)
        self.config_layout.addLayout(user_layout)

        where_group = QGroupBox("Insert where:")
        where_layout = QVBoxLayout()

        self.randomize_where_prefix = QRadioButton("Prefix")
        self.randomize_where_prefix.setChecked(True)
        self.randomize_where_suffix = QRadioButton("Suffix")
        self.randomize_where_position = QRadioButton("Position:")
        self.randomize_where_position_value = QSpinBox()
        self.randomize_where_position_value.setValue(1)
        self.randomize_where_position_value.setEnabled(False)
        self.randomize_where_position.toggled.connect(self.randomize_where_position_value.setEnabled)

        self.randomize_where_replace = QRadioButton("Replace current name")

        where_layout.addWidget(self.randomize_where_prefix)
        where_layout.addWidget(self.randomize_where_suffix)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.randomize_where_position)
        pos_layout.addWidget(self.randomize_where_position_value)
        pos_layout.addStretch()
        where_layout.addLayout(pos_layout)

        where_layout.addWidget(self.randomize_where_replace)
        where_group.setLayout(where_layout)
        self.config_layout.addWidget(where_group)

        self.randomize_skip_extension = QCheckBox("Skip extension")
        self.randomize_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.randomize_skip_extension)

    def show_padding_config(self):
        num_group = QGroupBox("Number sequences")
        num_layout = QVBoxLayout()

        add_padding_layout = QHBoxLayout()
        self.padding_add_check = QCheckBox()
        self.padding_add_check.setChecked(False)
        add_padding_label = QLabel("Add zero padding to length:")
        self.padding_add_length = QSpinBox()
        self.padding_add_length.setValue(1)
        self.padding_add_length.setMinimum(1)
        self.padding_add_length.setEnabled(False)
        self.padding_add_check.toggled.connect(self.padding_add_length.setEnabled)
        self.padding_add_check.stateChanged.connect(self.on_padding_add_toggled)

        add_padding_layout.addWidget(self.padding_add_check)
        add_padding_layout.addWidget(add_padding_label)
        add_padding_layout.addWidget(self.padding_add_length)
        add_padding_layout.addStretch()
        num_layout.addLayout(add_padding_layout)

        self.padding_remove_check = QCheckBox("Remove zero padding")
        self.padding_remove_check.setChecked(False)
        self.padding_remove_check.stateChanged.connect(self.on_padding_remove_toggled)
        num_layout.addWidget(self.padding_remove_check)

        which_layout = QVBoxLayout()
        which_label = QLabel("Process:")
        which_layout.addWidget(which_label)

        which_radio_layout = QHBoxLayout()
        self.padding_which_all = QRadioButton("All")
        self.padding_which_all.setChecked(True)
        self.padding_which_first = QRadioButton("First")
        self.padding_which_last = QRadioButton("Last")

        which_radio_layout.addWidget(self.padding_which_all)
        which_radio_layout.addWidget(self.padding_which_first)
        which_radio_layout.addWidget(self.padding_which_last)
        which_radio_layout.addStretch()
        which_layout.addLayout(which_radio_layout)
        num_layout.addLayout(which_layout)

        num_group.setLayout(num_layout)
        self.config_layout.addWidget(num_group)

        self.padding_skip_extension = QCheckBox("Skip extension")
        self.padding_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.padding_skip_extension)

    def show_clean_up_config(self):
        brackets_group = QGroupBox("Strip out content of brackets:")
        brackets_layout = QHBoxLayout()

        self.cleanup_brackets_round = QCheckBox("(...)")
        self.cleanup_brackets_square = QCheckBox("[...]")
        self.cleanup_brackets_curly = QCheckBox("{...}")

        brackets_layout.addWidget(self.cleanup_brackets_round)
        brackets_layout.addWidget(self.cleanup_brackets_square)
        brackets_layout.addWidget(self.cleanup_brackets_curly)
        brackets_layout.addStretch()

        brackets_group.setLayout(brackets_layout)
        self.config_layout.addWidget(brackets_group)

        replace_group = QGroupBox("Replace these characters with spaces:")
        replace_layout = QHBoxLayout()

        self.cleanup_replace_dot = QCheckBox("(dot)")
        self.cleanup_replace_comma = QCheckBox("(comma)")
        self.cleanup_replace_underscore = QCheckBox("_")
        self.cleanup_replace_dash = QCheckBox("-")
        self.cleanup_replace_percent20 = QCheckBox("%20")

        replace_layout.addWidget(self.cleanup_replace_dot)
        replace_layout.addWidget(self.cleanup_replace_comma)
        replace_layout.addWidget(self.cleanup_replace_underscore)
        replace_layout.addWidget(self.cleanup_replace_dash)
        replace_layout.addWidget(self.cleanup_replace_percent20)
        replace_layout.addStretch()

        replace_group.setLayout(replace_layout)
        self.config_layout.addWidget(replace_group)

        self.cleanup_skip_number_sequences = QCheckBox("Skip number sequences, (e.g. v1.2.4)")
        self.config_layout.addWidget(self.cleanup_skip_number_sequences)

        self.cleanup_camel_case = QCheckBox("Insert a space in front of capitalized letters (e.g. MyFile)")
        self.config_layout.addWidget(self.cleanup_camel_case)

        self.cleanup_fix_spaces = QCheckBox("Fix spaces: only one space at a time, no spaces on sides of basename")
        self.cleanup_fix_spaces.setChecked(True)
        self.config_layout.addWidget(self.cleanup_fix_spaces)

        self.cleanup_normalize_unicode = QCheckBox("Normalize unicode spaces by replacing them with a standard space")
        self.cleanup_normalize_unicode.setChecked(True)
        self.config_layout.addWidget(self.cleanup_normalize_unicode)

        self.cleanup_strip_unicode_marks = QCheckBox("Strip unicode marks (combining diacritics, accents)")
        self.config_layout.addWidget(self.cleanup_strip_unicode_marks)

        self.cleanup_skip_extension = QCheckBox("Skip extension")
        self.cleanup_skip_extension.setChecked(True)
        self.config_layout.addWidget(self.cleanup_skip_extension)

    def on_insert_meta_tag_toggled(self):
        self.insert_meta_tag_list.setVisible(self.insert_meta_tag.isChecked())

    def on_insert_meta_tag_selected(self):
        selected_item = self.insert_meta_tag_list.currentItem()
        if selected_item:
            tag = selected_item.text()
            current_text = self.insert_text.text()
            self.insert_text.setText(current_text + tag)

    def on_delete_current_name_toggled(self):
        is_checked = self.delete_current_name.isChecked()
        self.delete_from_group.setEnabled(not is_checked)
        self.delete_until_group.setEnabled(not is_checked)
        self.delete_do_not_remove_delimiters.setEnabled(not is_checked)

    def on_replace_meta_tag_toggled(self):
        self.replace_meta_tag_list.setVisible(self.replace_meta_tag.isChecked())

    def on_replace_meta_tag_selected(self):
        selected_item = self.replace_meta_tag_list.currentItem()
        if selected_item:
            tag = selected_item.text()
            current_text = self.replace_replace.text()
            self.replace_replace.setText(current_text + tag)

    def on_case_ext_lower_toggled(self):
        if self.case_ext_always_lower.isChecked():
            self.case_ext_always_upper.setChecked(False)

    def on_case_ext_upper_toggled(self):
        if self.case_ext_always_upper.isChecked():
            self.case_ext_always_lower.setChecked(False)

    def on_padding_add_toggled(self):
        if self.padding_add_check.isChecked():
            self.padding_remove_check.setChecked(False)

    def on_padding_remove_toggled(self):
        if self.padding_remove_check.isChecked():
            self.padding_add_check.setChecked(False)

    def _extract_rule_values(self):
        extractor = {
            "Insert": self._extract_insert,
            "Delete": self._extract_delete,
            "Replace": self._extract_replace,
            "Strip": self._extract_strip,
            "Case": self._extract_case,
            "Serialize": self._extract_serialize,
            "Randomize": self._extract_randomize,
            "Padding": self._extract_padding,
            "Clean Up": self._extract_cleanup
        }
        return extractor.get(self.selected_rule, {})()

    def _extract_insert(self):
        text = self.insert_text.text()
        if not text:
            return None

        if self.where_prefix.isChecked():
            where = "Prefix"
        elif self.where_suffix.isChecked():
            where = "Suffix"
        elif self.where_position.isChecked():
            where = f"Position:{self.where_position_value.value()}"
        elif self.where_after_text.isChecked():
            where = f"After text:{self.where_after_text_value.text()}"
        elif self.where_before_text.isChecked():
            where = f"Before text:{self.where_before_text_value.text()}"
        elif self.where_replace.isChecked():
            where = "Replace current name"
        else:
            where = "Prefix"

        return {
            "name": "Insert",
            "text": text,
            "meta_tag": self.insert_meta_tag.isChecked(),
            "where": where,
            "right_to_left": self.right_to_left.isChecked(),
            "skip_extension": self.insert_skip_extension.isChecked()
        }

    def _extract_delete(self):
        from_type = "Position" if self.delete_from_position.isChecked() else "Delimiter"
        from_value = self.delete_from_position_value.value() if from_type == "Position" else self.delete_from_delimiter_value.text()

        if self.delete_until_till_end.isChecked():
            until_type = "Till the end"
            until_value = ""
        elif self.delete_until_count.isChecked():
            until_type = "Count"
            until_value = self.delete_until_count_value.value()
        else:
            until_type = "Delimiter"
            until_value = self.delete_until_delimiter_value.text()

        return {
            "name": "Delete",
            "from_type": from_type,
            "from_value": from_value,
            "until_type": until_type,
            "until_value": until_value,
            "delete_current_name": self.delete_current_name.isChecked(),
            "skip_extension": self.delete_skip_extension.isChecked(),
            "right_to_left": self.delete_right_to_left.isChecked(),
            "do_not_remove_delimiters": self.delete_do_not_remove_delimiters.isChecked()
        }

    def _extract_replace(self):
        if self.replace_all.isChecked():
            occurrences = "All"
        elif self.replace_first.isChecked():
            occurrences = "First"
        else:
            occurrences = "Last"

        return {
            "name": "Replace",
            "find": self.replace_find.text(),
            "replace": self.replace_replace.text(),
            "occurrences": occurrences,
            "case_sensitive": self.replace_case_sensitive.isChecked(),
            "skip_extension": self.replace_skip_extension.isChecked()
        }

    def _extract_strip(self):
        chars_to_strip = ""
        if self.strip_english.isChecked():
            chars_to_strip += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if self.strip_digits.isChecked():
            chars_to_strip += "0123456789"
        if self.strip_symbols.isChecked():
            chars_to_strip += "!@#$%^&~-+=~.,"
        if self.strip_brackets.isChecked():
            chars_to_strip += "(){}[]"
        if self.strip_user.isChecked():
            chars_to_strip += self.strip_user_input.text()

        return {
            "name": "Strip",
            "characters": chars_to_strip,
            "invert": self.strip_invert.isChecked(),
            "case_sensitive": self.strip_case_sensitive.isChecked(),
            "skip_extension": self.strip_skip_extension.isChecked()
        }

    def _extract_case(self):
        if self.case_capitalize_every_word.isChecked():
            case_type = "Capitalize Every Word"
        elif self.case_capitalize_and_preserve.isChecked():
            case_type = "Capitalize AND Preserve"
        elif self.case_all_lower.isChecked():
            case_type = "all lower case"
        elif self.case_all_upper.isChecked():
            case_type = "ALL UPPER CASE"
        elif self.case_invert.isChecked():
            case_type = "iNVeRT cASE"
        else:
            case_type = "First letter capital"

        return {
            "name": "Case",
            "case_type": case_type,
            "ext_always_lower": self.case_ext_always_lower.isChecked(),
            "ext_always_upper": self.case_ext_always_upper.isChecked(),
            "skip_extension": self.case_skip_extension.isChecked()
        }

    def _extract_serialize(self):
        where = ""
        if self.serialize_where_prefix.isChecked():
            where = "Prefix"
        elif self.serialize_where_suffix.isChecked():
            where = "Suffix"
        elif self.serialize_where_position.isChecked():
            where = f"Position:{self.serialize_where_position_value.value()}"
        else:
            where = "Replace current name"

        return {
            "name": "Serialize",
            "index_starts": self.serialize_index_starts.value(),
            "repeat": self.serialize_repeat.value(),
            "step": self.serialize_step.value(),
            "reset_every": self.serialize_reset_every.value() if self.serialize_reset_every_check.isChecked() else None,
            "reset_if_folder_changes": self.serialize_reset_if_folder_changes.isChecked(),
            "pad_with_zeros": self.serialize_pad_check.isChecked(),
            "pad_length": self.serialize_pad_length.value(),
            "numbering_system": self.serialize_numbering_system.currentText(),
            "where": where,
            "skip_extension": self.serialize_skip_extension.isChecked()
        }

    def _extract_randomize(self):
        chars_to_use = ""
        if self.randomize_digits.isChecked():
            chars_to_use += "0123456789"
        if self.randomize_english.isChecked():
            chars_to_use += "abcdefghijklmnopqrstuvwxyz"
        if self.randomize_user.isChecked():
            chars_to_use += self.randomize_user_input.text()

        where = ""
        if self.randomize_where_prefix.isChecked():
            where = "Prefix"
        elif self.randomize_where_suffix.isChecked():
            where = "Suffix"
        elif self.randomize_where_position.isChecked():
            where = f"Position:{self.randomize_where_position_value.value()}"
        else:
            where = "Replace current name"

        return {
            "name": "Randomize",
            "length": self.randomize_length.value(),
            "characters": chars_to_use,
            "where": where,
            "skip_extension": self.randomize_skip_extension.isChecked()
        }

    def _extract_padding(self):
        add_padding = self.padding_add_check.isChecked()
        add_length = self.padding_add_length.value() if add_padding else 0
        remove_padding = self.padding_remove_check.isChecked()

        which = "All"
        if self.padding_which_first.isChecked():
            which = "First"
        elif self.padding_which_last.isChecked():
            which = "Last"

        return {
            "name": "Padding",
            "add_padding": add_padding,
            "add_length": add_length,
            "remove_padding": remove_padding,
            "which": which,
            "skip_extension": self.padding_skip_extension.isChecked()
        }

    def _extract_cleanup(self):
        return {
            "name": "Clean Up",
            "strip_round_brackets": self.cleanup_brackets_round.isChecked(),
            "strip_square_brackets": self.cleanup_brackets_square.isChecked(),
            "strip_curly_brackets": self.cleanup_brackets_curly.isChecked(),
            "replace_dot": self.cleanup_replace_dot.isChecked(),
            "replace_comma": self.cleanup_replace_comma.isChecked(),
            "replace_underscore": self.cleanup_replace_underscore.isChecked(),
            "replace_dash": self.cleanup_replace_dash.isChecked(),
            "replace_percent20": self.cleanup_replace_percent20.isChecked(),
            "skip_number_sequences": self.cleanup_skip_number_sequences.isChecked(),
            "camel_case_split": self.cleanup_camel_case.isChecked(),
            "fix_spaces": self.cleanup_fix_spaces.isChecked(),
            "normalize_unicode_spaces": self.cleanup_normalize_unicode.isChecked(),
            "strip_unicode_marks": self.cleanup_strip_unicode_marks.isChecked(),
            "skip_extension": self.cleanup_skip_extension.isChecked()
        }

class FileRenamerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Renamer")
        icon = os.path.join(getattr(sys,"_MEIPASS",os.path.dirname(__file__)),"icon.ico")
        os.path.exists(icon) and self.setWindowIcon(QIcon(icon))
        self.setGeometry(100, 100,500, 600)
        self.files = []
        self.file_paths = []
        self.rules = []
        self.undo_history = []
        self.pending_undo_state = None
        self.serialize_counter = {}
        self.randomize_used_values = {}
        self.init_ui()
        self.settings = QSettings("setting.ini", QSettings.Format.IniFormat)
        self.load_settings()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        action_layout = QHBoxLayout()

        folder_btn = QPushButton("Add Folder")
        folder_btn.clicked.connect(self.add_folder)
        files_btn = QPushButton("Add Files")
        files_btn.clicked.connect(self.add_files)
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self.apply_changes)
        self.rename_btn.setEnabled(False)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo)
        self.undo_btn.setEnabled(False)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset)

        action_layout.addWidget(folder_btn)
        action_layout.addWidget(files_btn)
        action_layout.addWidget(self.rename_btn)
        action_layout.addWidget(self.undo_btn)
        action_layout.addWidget(reset_btn)
        action_layout.addStretch()

        main_layout.addLayout(action_layout)

        rules_group = QGroupBox("Custom Rules")

        rules_layout = QVBoxLayout()
        rules_layout.setContentsMargins(0, 0, 0, 0)
        rules_layout.setSpacing(0)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)

        add_rule_btn = QToolButton()
        add_rule_btn.setText("+ Add")
        add_rule_btn.setMaximumWidth(80)
        add_rule_btn.setAutoRaise(True)
        add_rule_btn.clicked.connect(self.open_add_rule_dialog)
        delete_rule_btn = QToolButton()
        delete_rule_btn.setText("- Delete")
        delete_rule_btn.setMaximumWidth(90)
        delete_rule_btn.setAutoRaise(True)
        delete_rule_btn.clicked.connect(self.delete_selected_rules)
        edit_rule_btn = QToolButton()
        edit_rule_btn.setText("⟳ Edit")
        edit_rule_btn.setMaximumWidth(80)
        edit_rule_btn.setAutoRaise(True)
        edit_rule_btn.clicked.connect(self.edit_selected_rule)
        up_rule_btn = QToolButton()
        up_rule_btn.setText("▲ Up")
        up_rule_btn.setMaximumWidth(60)
        up_rule_btn.setAutoRaise(True)
        up_rule_btn.clicked.connect(self.move_rule_up)
        down_rule_btn = QToolButton()
        down_rule_btn.setText("▼ Down")
        down_rule_btn.setMaximumWidth(60)
        down_rule_btn.setAutoRaise(True)
        down_rule_btn.clicked.connect(self.move_rule_down)

        buttons_layout.addWidget(add_rule_btn)
        buttons_layout.addWidget(delete_rule_btn)
        buttons_layout.addWidget(edit_rule_btn)
        buttons_layout.addWidget(up_rule_btn)
        buttons_layout.addWidget(down_rule_btn)
        buttons_layout.addStretch()

        import_rule_btn = QToolButton()
        import_rule_btn.setText("⤷ Import")
        import_rule_btn.setMaximumWidth(60)
        import_rule_btn.setAutoRaise(True)
        import_rule_btn.clicked.connect(self.import_rules)
        export_rule_btn = QToolButton()
        export_rule_btn.setText("⤶ Export")
        export_rule_btn.setMaximumWidth(60)
        export_rule_btn.setAutoRaise(True)
        export_rule_btn.clicked.connect(self.export_rules)

        buttons_layout.addWidget(import_rule_btn)
        buttons_layout.addWidget(export_rule_btn)

        self.rules_placeholder = ClickableRulePlaceholder("Click here to add a rule")
        self.rules_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.rules_placeholder.font()
        font.setPointSize(12)
        self.rules_placeholder.setFont(font)
        self.rules_placeholder.setStyleSheet("color: #0066cc;")
        self.rules_placeholder.clicked.connect(self.open_add_rule_dialog)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(3)
        self.rules_table.setHorizontalHeaderLabels(["", "Rule", "Description"])
        self.rules_table.setColumnWidth(0, 30)
        self.rules_table.setColumnWidth(1, 80)
        self.rules_table.setColumnWidth(2, 400)
        for i in range(self.rules_table.columnCount()):
            item = self.rules_table.horizontalHeaderItem(i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rules_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.rules_table.itemDoubleClicked.connect(self.edit_selected_rule)
        clickable_rule_table = self.rules_table.mousePressEvent
        def clickable_rule_table_handler(event):
            if self.rules_table.itemAt(event.pos()) is None and event.button() == Qt.MouseButton.LeftButton:
                self.open_add_rule_dialog()
            else:
                clickable_rule_table(event)
        self.rules_table.mousePressEvent = clickable_rule_table_handler

        rules_stacked = QStackedWidget()
        rules_stacked.addWidget(self.rules_placeholder)
        rules_stacked.addWidget(self.rules_table)
        self.rules_stacked = rules_stacked

        rules_layout.addLayout(buttons_layout)
        rules_layout.addWidget(rules_stacked)

        rules_group.setLayout(rules_layout)

        preview_widget = QWidget()

        preview_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(QLabel("Preview:"))
        self.include_subfolders = QCheckBox("Include files from subfolders")
        self.include_subfolders.setChecked(False)
        header_layout.addStretch()
        header_layout.addWidget(self.include_subfolders)

        self.preview_placeholder = DragDropPlaceholder("Drag your files or folders here")
        self.preview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.preview_placeholder.font()
        font.setPointSize(12)
        self.preview_placeholder.setFont(font)
        self.preview_placeholder.setStyleSheet("color: #0066cc;")
        self.preview_placeholder.files_dropped.connect(self.handle_dropped_files)

        self.preview_table = DragDropTable()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(["", "Original Name", "New Name", "State", "Path"])
        self.preview_table.setColumnWidth(0, 20)
        self.preview_table.setColumnWidth(1, 150)
        self.preview_table.setColumnWidth(2, 150)
        self.preview_table.setColumnWidth(3, 50)
        self.preview_table.setColumnWidth(4, 400)
        for i in range(self.preview_table.columnCount()):
            item = self.preview_table.horizontalHeaderItem(i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.preview_table.files_dropped.connect(self.handle_dropped_files)

        preview_stacked = QStackedWidget()
        preview_stacked.addWidget(self.preview_placeholder)
        preview_stacked.addWidget(self.preview_table)
        self.preview_stacked = preview_stacked

        preview_layout.addLayout(header_layout)
        preview_layout.addWidget(preview_stacked)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_widget.setLayout(preview_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(rules_group)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        central_widget.setLayout(main_layout)

        self.override_table_key_press()

    def load_settings(self):
        include_sub = self.settings.value("Settings/include_subfolders", False, type=bool)
        self.include_subfolders.setChecked(include_sub)
        rules_str = self.settings.value("Settings/rules", "[]", type=str)
        try:
            self.rules = json.loads(rules_str)
            if self.rules:
                self.update_rules_table()
                self.rules_stacked.setCurrentWidget(self.rules_table)
        except Exception as e:
            print(f"Không thể load rules: {e}")
            self.rules = []

        geometry = self.settings.value("Window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
    def save_settings(self):
        self.settings.setValue("Settings/include_subfolders", self.include_subfolders.isChecked())
        self.settings.setValue("Settings/rules", json.dumps(self.rules, ensure_ascii=False))
        self.settings.setValue("Window/geometry", self.saveGeometry())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if self.include_subfolders.isChecked():
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_paths:
                            self.file_paths.append(file_path)
                            self.files.append(file)
            else:
                folder_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
                for file in folder_files:
                    file_path = os.path.join(folder, file)
                    if file_path not in self.file_paths:
                        self.file_paths.append(file_path)
                        self.files.append(file)

            self.update_table()
            self.apply_rules()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        if files:
            for file in files:
                if file not in self.file_paths:
                    self.file_paths.append(file)
                    self.files.append(os.path.basename(file))

            self.update_table()
            self.apply_rules()

    def apply_changes(self):
        operations = []
        history_items = []

        for i in range(len(self.files)):
            container = self.preview_table.cellWidget(i, 0)
            if container:
                checkbox = container.layout().itemAt(1).widget()
                if checkbox and checkbox.isChecked():
                    original = self.preview_table.item(i, 1).text()
                    new = self.preview_table.item(i, 2).text()

                    if original != new:
                        old_path = self.file_paths[i]
                        new_path = os.path.join(os.path.dirname(old_path), new)
                        operations.append((old_path, new_path))
                        history_items.append({
                            "row": i,
                            "before": original,
                            "after": new,
                            "old_path": old_path,
                            "new_path": new_path
                        })

        if not operations:
            QMessageBox.information(self, "Info", "No changes to apply")
            return

        reply = QMessageBox.question(self, "Confirm", f"Rename {len(operations)} file(s)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.undo_history.append({"items": history_items})
            self.worker = RenameWorker(operations)
            self.worker.finished.connect(self.on_rename_finished)
            self.worker.start()

    def undo(self):
        if not self.undo_history:
            QMessageBox.information(self, "Info", "No undo history")
            return

        last_state = self.undo_history.pop()
        undos = []
        for item in last_state["items"]:
            undos.append((item["new_path"], item["old_path"]))

        if not undos:
            QMessageBox.information(self, "Info", "No undo history")
            return

        self.pending_undo_state = last_state
        self.undo_btn.setEnabled(False)

        self.worker = RenameWorker(undos)
        self.worker.finished.connect(self.on_undo_finished)
        self.worker.start()

    def reset(self):
        self.preview_table.setRowCount(0)
        self.files = []
        self.file_paths = []
        self.rules = []
        self.rules_table.setRowCount(0)
        self.undo_history = []
        self.rename_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.pending_undo_state = None

    def update_table(self):
        self.preview_table.setRowCount(len(self.files))
        for i, file in enumerate(self.files):
            checkbox_container, checkbox = self.create_checkbox(True)

            original_item = QTableWidgetItem(file)
            new_item = QTableWidgetItem(file)
            state_item = QTableWidgetItem()
            path_item = QTableWidgetItem(self.file_paths[i])

            original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            original_item.setToolTip("Double-click to edit")
            new_item.setToolTip("Double-click to edit")
            state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            state_item.setToolTip("Double-click to edit")
            path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            path_item.setToolTip("Double-click to edit")

            self.preview_table.setCellWidget(i, 0, checkbox_container)
            self.preview_table.setItem(i, 1, original_item)
            self.preview_table.setItem(i, 2, new_item)
            self.preview_table.setItem(i, 3, state_item)
            self.preview_table.setItem(i, 4, path_item)

            self.preview_stacked.setCurrentWidget(self.preview_table)

    def apply_rules(self):
        self.serialize_counter = {}
        self.randomize_used_values = {}

        new_names = []
        for i, file in enumerate(self.files):
            new_name = file
            for row in range(self.rules_table.rowCount()):
                container = self.rules_table.cellWidget(row, 0)
                if container:
                    checkbox = container.layout().itemAt(1).widget()
                    if checkbox and checkbox.isChecked():
                        rule = self.rules[row]
                        new_name = self.apply_single_rule(new_name, rule, self.file_paths[i])

            new_names.append(new_name)
            self.preview_table.item(i, 2).setText(new_name)

        has_error = False
        seen_names = {}
        duplicate_list = []
        forbidden_list = []
        empty_list = []

        for i, new_name in enumerate(new_names):
            state_item = self.preview_table.item(i, 3)

            if not new_name or new_name.strip() == "":
                state_item.setText("✖")
                has_error = True
                if new_name not in empty_list:
                    empty_list.append(new_name if new_name else "(empty)")
            elif self.has_forbidden_characters(new_name):
                state_item.setText("✖")
                has_error = True
                if new_name not in forbidden_list:
                    forbidden_list.append(new_name)
            else:
                file_dir = os.path.dirname(self.file_paths[i])
                name_key = (file_dir, new_name)

                if name_key in seen_names:
                    state_item.setText("✖")
                    has_error = True
                    if new_name not in duplicate_list:
                        duplicate_list.append(new_name)
                else:
                    state_item.setText("✔")
                    seen_names[name_key] = i

        if has_error:
            error_message = ""
            if empty_list:
                error_message += "Empty filenames detected (New Name cannot be empty)\n"
                error_message += f"Files: {', '.join(empty_list[:3])}"
                if len(empty_list) > 3:
                    error_message += "..."
                error_message += "\n\n"
            if forbidden_list:
                error_message += "Forbidden characters detected: \\/:*?\"<>|\n"
                forbidden_text = ", ".join(forbidden_list[:3])
                if len(forbidden_list) > 3:
                    forbidden_text += "..."
                error_message += f"Files: {forbidden_text}\n\n"
            if duplicate_list:
                error_message += "Duplicate filenames detected"

            QMessageBox.warning(self, "Warning", error_message)

        self.rename_btn.setEnabled(not has_error and len(self.files) > 0)

    def on_rename_finished(self, success: bool, message: str):
        if success:
            if self.undo_history:
                last_state = self.undo_history[-1]
                for item in last_state["items"]:
                    row = item["row"]
                    new_name = item["after"]
                    new_path = item["new_path"]
                    self.files[row] = new_name
                    self.file_paths[row] = new_path
                    self.preview_table.item(row, 1).setText(new_name)
                    self.preview_table.item(row, 2).setText(new_name)
                    self.preview_table.item(row, 4).setText(new_path)
            self.undo_btn.setEnabled(True)
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def on_undo_finished(self, success: bool, message: str):
        if success:
            for item in self.pending_undo_state["items"]:
                row = item["row"]
                old_name = item["before"]
                old_path = item["old_path"]
                self.files[row] = old_name
                self.file_paths[row] = old_path
                self.preview_table.item(row, 1).setText(old_name)
                self.preview_table.item(row, 2).setText(old_name)
                self.preview_table.item(row, 4).setText(old_path)
            if self.rules_table.rowCount() > 0:
                self.rules_stacked.setCurrentWidget(self.rules_table)
            self.apply_rules()
            QMessageBox.information(self, "Info", "Undo completed")
        else:
            self.undo_history.append(self.pending_undo_state)
            QMessageBox.critical(self, "Error", message)

        self.pending_undo_state = None
        if not self.undo_history:
            self.undo_btn.setEnabled(False)

    def open_add_rule_dialog(self):
        dialog = AddRuleDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_rule = dialog.selected_rule
            rule_config = dialog.rule_config

            if selected_rule and rule_config:
                self.rules.append(rule_config)

                row = self.rules_table.rowCount()
                self.rules_table.insertRow(row)

                checkbox_container, checkbox = self.create_checkbox(True)
                checkbox.stateChanged.connect(self.on_rule_toggled)
                self.rules_table.setCellWidget(row, 0, checkbox_container)

                rule_item = QTableWidgetItem(selected_rule)
                rule_item.setFlags(rule_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                rule_item.setToolTip("Double click to edit")
                self.rules_table.setItem(row, 1, rule_item)

                description = self.generate_rule_description(rule_config)
                description_item = QTableWidgetItem(description)
                description_item.setFlags(description_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                description_item.setToolTip("Double click to edit")
                self.rules_table.setItem(row, 2, description_item)

                self.rules_stacked.setCurrentWidget(self.rules_table)
                self.apply_rules()

    def delete_selected_rules(self):
        selected_rows = sorted(set(index.row() for index in self.rules_table.selectedIndexes()), reverse=True)
        for row in selected_rows:
            self.rules_table.removeRow(row)
            self.rules.pop(row)

        self.apply_rules()

    def edit_selected_rule(self):
        selected_rows = sorted(set(index.row() for index in self.rules_table.selectedIndexes()))
        if not selected_rows:
            return

        row = selected_rows[0]
        rule_config = self.rules[row]

        dialog = AddRuleDialog(self, rule_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_rule = dialog.selected_rule
            updated_config = dialog.rule_config
            if selected_rule and updated_config:
                self.rules[row] = updated_config

                rule_item = self.rules_table.item(row, 1)
                rule_item.setText(selected_rule)
                rule_item.setToolTip("Double click to edit")

                description = self.generate_rule_description(updated_config)
                description_item = self.rules_table.item(row, 2)
                description_item.setText(description)
                description_item.setToolTip("Double click to edit")

                self.apply_rules()

    def move_rule_up(self):
        selected_rows = sorted(set(index.row() for index in self.rules_table.selectedIndexes()))

        if not selected_rows or selected_rows[0] == 0:
            return

        for row in selected_rows:
            if row > 0:
                self.rules[row], self.rules[row - 1] = self.rules[row - 1], self.rules[row]

        self.update_rules_table()

        self.rules_table.clearSelection()
        for row in selected_rows:
            if row > 0:
                self.rules_table.selectRow(row - 1)

        self.apply_rules()

    def move_rule_down(self):
        selected_rows = sorted(set(index.row() for index in self.rules_table.selectedIndexes()), reverse=True)

        if not selected_rows or selected_rows[0] == self.rules_table.rowCount() - 1:
            return

        for row in selected_rows:
            if row < self.rules_table.rowCount() - 1:
                self.rules[row], self.rules[row + 1] = self.rules[row + 1], self.rules[row]

        self.update_rules_table()

        self.rules_table.clearSelection()
        for row in selected_rows:
            if row < self.rules_table.rowCount() - 1:
                self.rules_table.selectRow(row + 1)

        self.apply_rules()

    def export_rules(self):
        if not self.rules:
            QMessageBox.warning(self, "Warning", "No rules to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(self,
            "Export Rules",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Success", f"Rules exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export rules:\n{str(e)}")

    def import_rules(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Rules",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_rules = json.load(f)

            if not isinstance(imported_rules, list):
                QMessageBox.warning(self, "Error", "Invalid rules file format. Expected a list of rules.")
                return

            reply = QMessageBox.question(self, "Import Rules", f"Import {len(imported_rules)} rule(s)? Current rules will be kept.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for rule_config in imported_rules:
                    if isinstance(rule_config, dict) and "name" in rule_config:
                        self.rules.append(rule_config)

                self.update_rules_table()
                self.rules_stacked.setCurrentWidget(self.rules_table)
                self.apply_rules()
                QMessageBox.information(self, "Success", f"{len(imported_rules)} rule(s) imported successfully")

        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Invalid JSON file format")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import rules:\n{str(e)}")

    def create_checkbox(self, checked=True):
        container = QWidget()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(checked)

        layout.addStretch()
        layout.addWidget(checkbox)
        layout.addStretch()

        container.setLayout(layout)

        return container, checkbox

    def update_rules_table(self):
        self.rules_table.setRowCount(len(self.rules))
        for row, rule in enumerate(self.rules):
            checkbox_container, checkbox = self.create_checkbox(True)
            checkbox.stateChanged.connect(self.on_rule_toggled)
            self.rules_table.setCellWidget(row, 0, checkbox_container)

            selected_rule = rule["name"]
            rule_item = QTableWidgetItem(selected_rule)
            rule_item.setFlags(rule_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            rule_item.setToolTip("Double click to edit")
            self.rules_table.setItem(row, 1, rule_item)

            description = self.generate_rule_description(rule)
            description_item = QTableWidgetItem(description)
            description_item.setFlags(description_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            description_item.setToolTip("Double click to edit")
            self.rules_table.setItem(row, 2, description_item)

    def on_rule_toggled(self):
        self.apply_rules()

    def has_forbidden_characters(self, filename):
        forbidden_chars = r'\/:*?"<>|'
        return any(char in filename for char in forbidden_chars)

    def handle_dropped_files(self, paths):
        for path in paths:
            if os.path.isfile(path):
                if path not in self.file_paths:
                    self.file_paths.append(path)
                    self.files.append(os.path.basename(path))
            elif os.path.isdir(path):
                if self.include_subfolders.isChecked():
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if file_path not in self.file_paths:
                                self.file_paths.append(file_path)
                                self.files.append(file)
                else:
                    folder_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                    for file in folder_files:
                        file_path = os.path.join(path, file)
                        if file_path not in self.file_paths:
                            self.file_paths.append(file_path)
                            self.files.append(file)

        self.update_table()
        self.apply_rules()

    def override_table_key_press(self):
        original_rules_keypress = QTableWidget.keyPressEvent
        def rules_keypress(event):
            if event.key() == Qt.Key.Key_Delete:
                self.delete_selected_rules()
            else:
                original_rules_keypress(self.rules_table, event)
        self.rules_table.keyPressEvent = rules_keypress

        original_table_keypress = self.preview_table.keyPressEvent
        def table_keypress(event):
            if event.key() == Qt.Key.Key_Delete:
                self.delete_selected_files()
            else:
                original_table_keypress(event)
        self.preview_table.keyPressEvent = table_keypress

    def delete_selected_files(self):
        selected_rows = sorted(set(index.row() for index in self.preview_table.selectedIndexes()), reverse=True)
        for row in selected_rows:
            self.preview_table.removeRow(row)
            self.file_paths.pop(row)
            self.files.pop(row)

    def generate_rule_description(self, rule_config):
        if rule_config["name"] == "Insert":
            text = rule_config["text"]
            where = rule_config["where"]
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""
            right_to_left_text = " (right-to-left)" if rule_config.get("right_to_left", False) else ""

            if where == "Replace current name":
                return f"Replace current name with '{text}'{skip_ext_text}"

            return f"Insert '{text}' at {where}{skip_ext_text}{right_to_left_text}"

        elif rule_config["name"] == "Delete":
            if rule_config.get("delete_current_name", False):
                skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""
                return f"Delete current name{skip_ext_text}"

            from_type = rule_config.get("from_type", "Position")
            from_value = rule_config.get("from_value", "1")
            until_type = rule_config.get("until_type", "Count")
            until_value = rule_config.get("until_value", "1")
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""
            right_to_left_text = " (right-to-left)" if rule_config.get("right_to_left", False) else ""
            keep_delim_text = " (keep delimiters)" if rule_config.get("do_not_remove_delimiters", False) else ""

            return f"Delete from {from_type} {from_value} until {until_type} {until_value}{skip_ext_text}{right_to_left_text}{keep_delim_text}"

        elif rule_config["name"] == "Replace":
            find = rule_config.get("find", "")
            replace = rule_config.get("replace", "")
            occurrences = rule_config.get("occurrences", "All")
            case_text = " (case sensitive)" if rule_config.get("case_sensitive", False) else ""
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return f"Replace '{find}' with '{replace}' ({occurrences}){case_text}{skip_ext_text}"

        elif rule_config["name"] == "Strip":
            chars = rule_config.get("characters", "")
            if not chars:
                return "Strip characters from filenames"

            invert_text = " (except selected)" if rule_config.get("invert", False) else ""
            case_text = " (case sensitive)" if rule_config.get("case_sensitive", False) else ""
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""
            char_display = chars[:20] + "..." if len(chars) > 20 else chars

            return f"Strip '{char_display}'{invert_text}{case_text}{skip_ext_text}"

        elif rule_config["name"] == "Case":
            case_type = rule_config.get("case_type", "Capitalize Every Word")
            ext_lower_text = " (ext lower)" if rule_config.get("ext_always_lower", False) else ""
            ext_upper_text = " (ext upper)" if rule_config.get("ext_always_upper", False) else ""
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return f"{case_type}{ext_lower_text}{ext_upper_text}{skip_ext_text}"

        elif rule_config["name"] == "Serialize":
            index_starts = rule_config.get("index_starts", 1)
            repeat = rule_config.get("repeat", 1)
            step = rule_config.get("step", 1)
            where = rule_config.get("where", "Prefix")
            pad_text = " (padded)" if rule_config.get("pad_with_zeros", False) else ""
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return f"Serialize from {index_starts} (repeat {repeat}, step {step}) at {where}{pad_text}{skip_ext_text}"

        elif rule_config["name"] == "Randomize":
            length = rule_config.get("length", 1)
            where = rule_config.get("where", "Prefix")
            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return f"Randomize {length} character(s) at {where}{skip_ext_text}"

        elif rule_config["name"] == "Padding":
            add_text = f"add {rule_config.get('add_length', 1)} zeros" if rule_config.get("add_padding", False) else ""
            remove_text = "remove zeros" if rule_config.get("remove_padding", False) else ""
            which = rule_config.get("which", "All")

            if add_text or remove_text:
                separator = " and " if (add_text and remove_text) else ""
                result = f"Padding ({add_text}{separator}{remove_text}) {which}"
            else:
                result = "Padding (no operation)"

            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return result + skip_ext_text

        elif rule_config["name"] == "Clean Up":
            options = []
            if rule_config.get("strip_round_brackets", False):
                options.append("(...) ")
            if rule_config.get("strip_square_brackets", False):
                options.append("[...] ")
            if rule_config.get("strip_curly_brackets", False):
                options.append("{...} ")
            if rule_config.get("replace_dot", False):
                options.append(".")
            if rule_config.get("replace_comma", False):
                options.append(",")
            if rule_config.get("replace_underscore", False):
                options.append("_")
            if rule_config.get("replace_dash", False):
                options.append("-")
            if rule_config.get("replace_percent20", False):
                options.append("%20")

            desc = "Clean up"
            if options:
                desc += f" (strip/replace: {', '.join(options).strip()})"
            if rule_config.get("skip_number_sequences", False):
                desc += " skip numbers"
            if rule_config.get("camel_case_split", False):
                desc += " split camelCase"

            skip_ext_text = " (skip extension)" if rule_config.get("skip_extension", False) else ""

            return desc + skip_ext_text

    def apply_single_rule(self, filename, rule, file_path=None):
        if rule["name"] == "Insert":
            text = rule["text"]
            where = rule["where"]
            skip_ext = rule["skip_extension"]
            right_to_left = rule["right_to_left"]

            if file_path and "{" in text and "}" in text:
                text = self.replace_meta_tags(text, file_path)

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if where == "Prefix":
                new_name = text + name_part
            elif where == "Suffix":
                new_name = name_part + text
            elif where.startswith("Position:"):
                pos = int(where.split(":")[1])
                if right_to_left:
                    pos = len(name_part) - pos + 1
                new_name = name_part[:pos] + text + name_part[pos:]
            elif where.startswith("After text:"):
                search_text = where.split(":", 1)[1]
                idx = name_part.find(search_text)
                if idx != -1:
                    new_name = name_part[:idx + len(search_text)] + text + name_part[idx + len(search_text):]
                else:
                    new_name = name_part
            elif where.startswith("Before text:"):
                search_text = where.split(":", 1)[1]
                idx = name_part.find(search_text)
                if idx != -1:
                    new_name = name_part[:idx] + text + name_part[idx:]
                else:
                    new_name = name_part
            elif where == "Replace current name":
                new_name = text
            else:
                new_name = name_part

            return new_name + ext

        elif rule["name"] == "Delete":
            if rule.get("delete_current_name"):
                skip_ext = rule.get("skip_extension", True)
                if skip_ext and "." in filename:
                    name_part, ext = filename.rsplit(".", 1)
                    return "." + ext
                else:
                    return ""

            skip_ext = rule.get("skip_extension", True)
            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            from_type = rule.get("from_type", "Position")
            from_value = rule.get("from_value", 1)
            until_type = rule.get("until_type", "Count")
            until_value = rule.get("until_value", 1)
            right_to_left = rule.get("right_to_left", False)
            keep_delimiters = rule.get("do_not_remove_delimiters", False)

            if from_type == "Position":
                start = from_value - 1
                if right_to_left:
                    start = len(name_part) - from_value
                start = max(0, start)
            else:
                idx = name_part.find(str(from_value))
                start = idx + len(str(from_value)) if idx != -1 else 0
                if not keep_delimiters and idx != -1:
                    start = idx

            if until_type == "Till the end":
                end = len(name_part)
            elif until_type == "Count":
                end = start + until_value
            else:
                idx = name_part.find(str(until_value), start)
                end = idx + (0 if keep_delimiters else len(str(until_value))) if idx != -1 else len(name_part)

            new_name = name_part[:start] + name_part[end:]

            return new_name + ext

        elif rule["name"] == "Replace":
            find_text = rule.get("find", "")
            replace_text = rule.get("replace", "")
            occurrences = rule.get("occurrences", "All")
            case_sensitive = rule.get("case_sensitive", False)
            skip_ext = rule.get("skip_extension", True)

            if not find_text:
                return filename

            if file_path and "{" in replace_text and "}" in replace_text:
                replace_text = self.replace_meta_tags(replace_text, file_path)

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if case_sensitive:
                if occurrences == "All":
                    new_name = name_part.replace(find_text, replace_text)
                elif occurrences == "First":
                    new_name = name_part.replace(find_text, replace_text, 1)
                else:
                    idx = name_part.rfind(find_text)
                    if idx != -1:
                        new_name = name_part[:idx] + replace_text + name_part[idx + len(find_text):]
                    else:
                        new_name = name_part
            else:
                pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                if occurrences == "All":
                    new_name = pattern.sub(replace_text, name_part)
                elif occurrences == "First":
                    new_name = pattern.sub(replace_text, name_part, count=1)
                else:
                    matches = list(pattern.finditer(name_part))
                    if matches:
                        last_match = matches[-1]
                        new_name = name_part[:last_match.start()] + replace_text + name_part[last_match.end():]
                    else:
                        new_name = name_part

            return new_name + ext

        elif rule["name"] == "Strip":
            chars_to_strip = rule.get("characters", "")
            invert = rule.get("invert", False)
            case_sensitive = rule.get("case_sensitive", False)
            skip_ext = rule.get("skip_extension", True)

            if not chars_to_strip:
                return filename

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if case_sensitive:
                if invert:
                    new_name = "".join(c for c in name_part if c in chars_to_strip)
                else:
                    new_name = "".join(c for c in name_part if c not in chars_to_strip)
            else:
                chars_lower = chars_to_strip.lower()
                chars_upper = chars_to_strip.upper()
                chars_combined = chars_lower + chars_upper

                if invert:
                    new_name = "".join(c for c in name_part if c.lower() in chars_lower or c.upper() in chars_upper)
                else:
                    new_name = "".join(c for c in name_part if c not in chars_combined)

            return new_name + ext

        elif rule["name"] == "Case":
            case_type = rule.get("case_type", "Capitalize Every Word")
            ext_always_lower = rule.get("ext_always_lower", False)
            ext_always_upper = rule.get("ext_always_upper", False)
            skip_ext = rule.get("skip_extension", True)

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if case_type == "Capitalize Every Word":
                new_name = name_part.title()
            elif case_type == "Capitalize AND Preserve":
                words = name_part.split()
                new_name = " ".join(word[0].upper() + word[1:] if len(word) > 0 else "" for word in words)
            elif case_type == "all lower case":
                new_name = name_part.lower()
            elif case_type == "ALL UPPER CASE":
                new_name = name_part.upper()
            elif case_type == "iNVeRT cASE":
                new_name = name_part.swapcase()
            else:
                new_name = name_part[0].upper() + name_part[1:] if len(name_part) > 0 else ""

            if ext:
                if ext_always_lower:
                    ext = ext.lower()
                elif ext_always_upper:
                    ext = ext.upper()

            return new_name + ext

        elif rule["name"] == "Serialize":
            if not hasattr(self, 'serialize_counter'):
                self.serialize_counter = {}

            rule_key = str(id(rule))
            if rule_key not in self.serialize_counter:
                self.serialize_counter[rule_key] = {
                    "current_num": rule.get("index_starts", 1),
                    "last_folder": None,
                    "count_since_reset": 0
                }

            state = self.serialize_counter[rule_key]

            should_reset = False

            if rule.get("reset_if_folder_changes", False) and file_path:
                current_folder = os.path.dirname(file_path)
                if state["last_folder"] is not None and state["last_folder"] != current_folder:
                    should_reset = True
                state["last_folder"] = current_folder

            reset_every = rule.get("reset_every")
            if reset_every is not None and state["count_since_reset"] >= reset_every:
                should_reset = True

            if should_reset:
                state["current_num"] = rule.get("index_starts", 1)
                state["count_since_reset"] = 0

            current_num = state["current_num"]

            numbering_system = rule.get("numbering_system", "Decimal digits (0,9)")
            if numbering_system == "Decimal digits (0,9)":
                formatted_num = str(current_num)
            elif numbering_system == "Lowercase letters (a-z)":
                formatted_num = ""
                n = current_num
                while n > 0:
                    n -= 1
                    formatted_num = chr(97 + (n % 26)) + formatted_num
                    n //= 26
                if not formatted_num:
                    formatted_num = "a"
            elif numbering_system == "Uppercase letters (A-Z)":
                formatted_num = ""
                n = current_num
                while n > 0:
                    n -= 1
                    formatted_num = chr(65 + (n % 26)) + formatted_num
                    n //= 26
                if not formatted_num:
                    formatted_num = "A"
            elif numbering_system == "Lowercase Roman (i,ii,iii...)":
                formatted_num = self.decimal_to_roman(current_num, uppercase=False)
            else:
                formatted_num = self.decimal_to_roman(current_num, uppercase=True)

            pad_length = rule.get("pad_length", 1)
            if rule.get("pad_with_zeros", False) and numbering_system == "Decimal digits (0,9)":
                formatted_num = formatted_num.zfill(pad_length)

            where = rule.get("where", "Prefix")
            skip_ext = rule.get("skip_extension", True)

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if where == "Prefix":
                new_name = formatted_num + name_part
            elif where == "Suffix":
                new_name = name_part + formatted_num
            elif where.startswith("Position:"):
                pos = int(where.split(":")[1])
                new_name = name_part[:pos] + formatted_num + name_part[pos:]
            else:
                new_name = formatted_num

            step = rule.get("step", 1)
            state["current_num"] += step
            state["count_since_reset"] += 1

            return new_name + ext

        elif rule["name"] == "Randomize":
            length = rule.get("length", 1)
            characters = rule.get("characters", "0123456789")
            where = rule.get("where", "Prefix")
            skip_ext = rule.get("skip_extension", True)

            if not characters:
                return filename

            rule_id = id(rule)
            if rule_id not in self.randomize_used_values:
                self.randomize_used_values[rule_id] = set()

            max_attempts = 1000
            attempts = 0
            random_str = ""

            while attempts < max_attempts:
                random_str = "".join(random.choice(characters) for _ in range(length))
                if random_str not in self.randomize_used_values[rule_id]:
                    self.randomize_used_values[rule_id].add(random_str)
                    break
                attempts += 1

            if attempts == max_attempts and random_str in self.randomize_used_values[rule_id]:
                pass

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            if where == "Prefix":
                new_name = random_str + name_part
            elif where == "Suffix":
                new_name = name_part + random_str
            elif where.startswith("Position:"):
                pos = int(where.split(":")[1])
                new_name = name_part[:pos] + random_str + name_part[pos:]
            else:
                new_name = random_str

            return new_name + ext

        elif rule["name"] == "Padding":
            add_padding = rule.get("add_padding", False)
            add_length = rule.get("add_length", 1)
            remove_padding = rule.get("remove_padding", False)
            which = rule.get("which", "All")
            skip_ext = rule.get("skip_extension", True)

            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            result = name_part

            matches = list(re.finditer(r'\d+', result))

            if matches:
                matches_to_process = []
                if which == "All":
                    matches_to_process = matches
                elif which == "First":
                    matches_to_process = [matches[0]]
                elif which == "Last":
                    matches_to_process = [matches[-1]]

                for match in reversed(matches_to_process):
                    digits = match.group()
                    start_pos = match.start()
                    end_pos = match.end()

                    if remove_padding:
                        digits_stripped = digits.lstrip('0')
                        if not digits_stripped:
                            digits_stripped = '0'
                        digits = digits_stripped

                    if add_padding:
                        digits = digits.zfill(add_length)

                    result = result[:start_pos] + digits + result[end_pos:]

            return result + ext

        elif rule["name"] == "Clean Up":
            import unicodedata

            skip_ext = rule.get("skip_extension", True)
            if skip_ext and "." in filename:
                name_part, ext = filename.rsplit(".", 1)
                ext = "." + ext
            else:
                name_part = filename
                ext = ""

            result = name_part

            if rule.get("strip_round_brackets", False):
                result = re.sub(r'\([^)]*\)', '', result)
            if rule.get("strip_square_brackets", False):
                result = re.sub(r'\[[^\]]*\]', '', result)
            if rule.get("strip_curly_brackets", False):
                result = re.sub(r'\{[^}]*\}', '', result)

            if rule.get("camel_case_split", False):
                result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)

            if rule.get("replace_dot", False):
                result = result.replace(".", " ")
            if rule.get("replace_comma", False):
                result = result.replace(",", " ")
            if rule.get("replace_underscore", False):
                result = result.replace("_", " ")
            if rule.get("replace_dash", False):
                result = result.replace("-", " ")
            if rule.get("replace_percent20", False):
                result = result.replace("%20", " ")

            if rule.get("normalize_unicode_spaces", True):
                result = re.sub(r'[\s\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+', ' ', result)

            if rule.get("strip_unicode_marks", False):
                result = ''.join(c for c in unicodedata.normalize('NFD', result)
                                if unicodedata.category(c) != 'Mn')

            if rule.get("fix_spaces", True):
                result = re.sub(r' +', ' ', result)
                result = result.strip()

            return result + ext

        return filename

    def decimal_to_roman(self, num, uppercase=False):
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syms = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1

        if not uppercase:
            roman_num = roman_num.lower()

        return roman_num

    def replace_meta_tags(self, text, file_path):
        try:
            now = datetime.now()
            text = text.replace("{Date_Now}", now.strftime("%Y%m%d_%H%M%S"))
            text = text.replace("{Date_Now_YMD}", now.strftime("%Y%m%d"))
            text = text.replace("{Date_Now_Y-M-D}", now.strftime("%Y-%m-%d"))
            text = text.replace("{Date_Now_YMmD}", now.strftime("%Y%b%d").upper())
            text = text.replace("{Date_Now_Year}", now.strftime("%Y"))
            text = text.replace("{Date_Now_Month}", now.strftime("%m"))
            text = text.replace("{Date_Now_Day}", now.strftime("%d"))

            text = text.replace("{Time_Now_HMS}", now.strftime("%H%M%S"))
            text = text.replace("{Time_Now_H:M:S}", now.strftime("%H:%M:%S"))
            text = text.replace("{Time_Now_H}", now.strftime("%H"))
            text = text.replace("{Time_Now_M}", now.strftime("%M"))
            text = text.replace("{Time_Now_S}", now.strftime("%S"))

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_size_kb = file_size / 1024
                file_size_mb = file_size_kb / 1024
                file_size_gb = file_size_mb / 1024

                text = text.replace("{File_Size}", str(file_size))
                text = text.replace("{File_SizeBytes}", str(file_size))
                text = text.replace("{File_SizeKB}", f"{file_size_kb:.2f}")
                text = text.replace("{File_SizeMB}", f"{file_size_mb:.2f}")
                text = text.replace("{File_SizeGB}", f"{file_size_gb:.2f}")

                created_time = os.path.getctime(file_path)
                modified_time = os.path.getmtime(file_path)
                created_date = datetime.fromtimestamp(created_time)
                modified_date = datetime.fromtimestamp(modified_time)

                text = text.replace("{File_DateCreated}", created_date.strftime("%Y%m%d_%H%M%S"))
                text = text.replace("{File_DateCreated_YMD}", created_date.strftime("%Y%m%d"))
                text = text.replace("{File_DateCreated_Y-M-D}", created_date.strftime("%Y-%m-%d"))
                text = text.replace("{File_DateCreated_YMmD}", created_date.strftime("%Y%b%d").upper())

                text = text.replace("{File_DateModified}", modified_date.strftime("%Y%m%d_%H%M%S"))
                text = text.replace("{File_DateModified_YMD}", modified_date.strftime("%Y%m%d"))
                text = text.replace("{File_DateModified_Y-M-D}", modified_date.strftime("%Y-%m-%d"))
                text = text.replace("{File_DateModified_YMmD}", modified_date.strftime("%Y%b%d").upper())

                file_name = os.path.basename(file_path)
                file_name_without_ext = os.path.splitext(file_name)[0]
                file_ext = os.path.splitext(file_name)[1].lstrip('.')
                folder_path = os.path.dirname(file_path)
                folder_name = os.path.basename(folder_path)

                text = text.replace("{File_FilePath}", file_path)
                text = text.replace("{File_FileName}", file_name_without_ext)
                text = text.replace("{File_Extension}", file_ext)
                text = text.replace("{File_FolderName}", folder_name)
                text = text.replace("{File_FolderPath}", folder_path)
        except Exception as e:
            pass

        return text

def main():
    app = QApplication(sys.argv)
    window = FileRenamerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()