import json
import os
import sys
import pandas as pd
import numpy as np
import io
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, 
                               QLineEdit, QPushButton, QComboBox, QSpinBox, QFormLayout,
                               QLabel, QTableWidget, QTableWidgetItem, QDialogButtonBox,
                               QFileDialog, QMessageBox, QCheckBox, QSlider,QTabWidget, QWidget)
from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.widgets import RectangleSelector
from PySide6.QtCore import QObject, QThread, Signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.pylab as pylab
import re
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
from datetime import datetime
import scipy.signal as signal

# --- FIX: Make SettingsManager aware of the script's path ---
# This ensures Settings_CA.json is always saved next to BETA.py
SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class AddFractionDialog(QDialog):
    """A simple dialog to get position and label for a new fraction."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Fraction")
        layout = QFormLayout(self)
        self.pos_edit = QLineEdit()
        self.pos_edit.setValidator(QtGui.QDoubleValidator())
        self.label_edit = QLineEdit()
        layout.addRow("Position (mL):", self.pos_edit)
        layout.addRow("Label:", self.label_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        return self.pos_edit.text(), self.label_edit.text()

class SettingsManager:
    """Handles loading and saving all application settings to a single JSON file."""
    # --- FIX: Use an absolute path to the settings file ---
    SETTINGS_FILE = os.path.join(SCRIPT_DIRECTORY, "Settings_CA.json")
    
    @staticmethod
    def _get_default_plot_options():
        """Returns the factory-default plot options list."""
        return [
            # Plot styles (first 6)
            '-@b', '-@g', '-@r', '-@m', '-@c', '-@k', 
            # Font settings
            'Arial', '10', '10', 
            # Variable Names (11)
            'UV', 'pH', 'Conductivity', 'System Pressure', 'Gradient', 'Flow rate', 
            'Fraction', 'Injection', 'Pre-column Pressure', 'Variable 1', 'Variable 2',
            # Variable Units (11)
            ' (mAU)', '', ' (mS/cm)', ' (MPa)', '%', ' (mL/min)', 
            'Fraction', ' (mL/min)', ' (MPa)', '', '',
            # Processing options (last 3)
            'False', 'False', 'True'
        ]

    @staticmethod
    def _get_default_settings():
        """Returns the default structure for the settings file."""
        return {
            "plot_options": SettingsManager._get_default_plot_options(),
            "import_profiles": {}
        }

    @classmethod
    def load_settings(cls):
        """Loads settings from the JSON file, creating it if it doesn't exist."""
        if not os.path.exists(cls.SETTINGS_FILE):
            settings = cls._get_default_settings()
            cls.save_settings(settings)
            return settings
        try:
            with open(cls.SETTINGS_FILE, 'r') as f:
                loaded_settings = json.load(f)
                if "plot_options" not in loaded_settings or "import_profiles" not in loaded_settings:
                    raise ValueError("Settings file is missing required keys.")
                return loaded_settings
        except (json.JSONDecodeError, IOError, ValueError):
            print(f"Warning: Could not read {cls.SETTINGS_FILE}. Creating a new one.")
            settings = cls._get_default_settings()
            cls.save_settings(settings)
            return settings

    @classmethod
    def save_settings(cls, settings_data):
        """Saves the provided settings dictionary to the JSON file."""
        try:
            # The logic that reset variable names to default has been removed
            # to allow user-defined names to be saved permanently.
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(settings_data, f, indent=4)
        except IOError as e:
            print(f"Error saving settings to {cls.SETTINGS_FILE}: {e}")

    @classmethod
    def get_plot_options(cls):
        """Convenience method to get just the plot options."""
        return cls.load_settings().get("plot_options", cls._get_default_plot_options())

    @classmethod
    def get_import_profiles(cls):
        """Convenience method to get just the import profiles."""
        return cls.load_settings().get("import_profiles", {})

# --- Global variable initialization ---
output_options = SettingsManager.get_plot_options()
stop_var = 0
custom_updated = 0
fraction_lbl_size_main = int(output_options[8])
color_list = ["blue", "green", "red", "magenta", "cyan", "yellow", "Custom"]
style_list = ["-", "--", "-.", ":"]
variable_name = output_options[9:20]
variable_unit = output_options[20:31]
order_table = [variable_name[0], variable_name[1]]
units = dict([[y, variable_unit[x]] for x, y in enumerate(variable_name)])

class ImportWizard(QDialog):
    """
    A mode-based dialog for importing chromatogram data. Features a dedicated,
    one-click importer for standard ÄKTA Unicorn files and a flexible custom
    mode for other formats.
    """
    data_imported = QtCore.Signal(dict, str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Chromatogram Wizard")
        self.setMinimumSize(600, 200)
        
        self.source_filename = ""
        self.current_mode = None 
        self.mapping_controls = []

        main_layout = QVBoxLayout(self)

        # --- Step 1: File Selection and Mode Choice ---
        top_group = QGroupBox("1. Select File and Import Mode")
        top_layout = QVBoxLayout(top_group)
        
        file_layout = QHBoxLayout()
        self.filepath_edit = QLineEdit()
        self.filepath_edit.setReadOnly(True)
        self.filepath_edit.setPlaceholderText("No file selected...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_for_file)
        file_layout.addWidget(QLabel("File Path:"))
        file_layout.addWidget(self.filepath_edit)
        file_layout.addWidget(browse_btn)
        top_layout.addLayout(file_layout)
        
        mode_layout = QHBoxLayout()
        self.akta_btn = QPushButton("Load ÄKTA File")
        self.custom_btn = QPushButton("Custom Import")
        self.akta_btn.setEnabled(False)
        self.custom_btn.setEnabled(False)
        self.akta_btn.clicked.connect(self._handle_akta_import)
        self.custom_btn.clicked.connect(self._handle_custom_import)
        mode_layout.addStretch()
        mode_layout.addWidget(self.akta_btn)
        mode_layout.addWidget(self.custom_btn)
        mode_layout.addStretch()
        top_layout.addLayout(mode_layout)
        main_layout.addWidget(top_group)

        # --- Widgets for Custom Import Mode (initially hidden) ---
        self._create_custom_widgets()
        main_layout.addWidget(self.custom_options_group)
        main_layout.addWidget(self.mapping_group)
        main_layout.addWidget(self.profile_group)
        main_layout.addWidget(self.button_box)

        self._hide_custom_widgets()
        self._load_profiles_to_combo()

    def _create_custom_widgets(self):
        """Creates all widgets needed for the Custom Import path."""
        self.custom_options_group = QGroupBox("Custom Parsing Options")
        custom_layout = QHBoxLayout(self.custom_options_group)
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems(["Tab", "Comma", "Space"])
        self.header_spinbox = QSpinBox()
        self.header_spinbox.setRange(0, 100)
        self.preview_raw_checkbox = QCheckBox("Preview Raw File")
        self.preview_raw_checkbox.setChecked(False)
        custom_layout.addWidget(QLabel("Delimiter:"))
        custom_layout.addWidget(self.delimiter_combo)
        custom_layout.addWidget(QLabel("Header Row:"))
        custom_layout.addWidget(self.header_spinbox)
        custom_layout.addStretch()
        custom_layout.addWidget(self.preview_raw_checkbox)
        self.delimiter_combo.currentTextChanged.connect(self.load_and_preview)
        self.header_spinbox.valueChanged.connect(self.load_and_preview)
        self.preview_raw_checkbox.stateChanged.connect(self.populate_preview)

        self.mapping_group = QGroupBox("2. Map Data Columns")
        mapping_main_layout = QVBoxLayout(self.mapping_group)
        
        # --- MODIFICATION START ---
        
        # A grid just for the plottable Y-axis variables
        y_axis_grid_layout = QGridLayout()
        y_axis_grid_layout.addWidget(QLabel("<b>Variable Name (Editable)</b>"), 0, 0)
        y_axis_grid_layout.addWidget(QLabel("<b>Y-Axis (Data)</b>"), 0, 1)
        y_axis_grid_layout.addWidget(QLabel("<b>X-Axis (Volume/Time)</b>"), 0, 2)
        
        # This new list will only contain tuples for actual Y-axis variables
        self.y_axis_mapping_controls = []
        
        # Iterate through the global variable list to create controls
        for i, name in enumerate(variable_name):
            if name == 'Fraction': # Skip Fraction in this section
                continue
            
            name_edit = QLineEdit(name)
            y_combo, x_combo = QComboBox(), QComboBox()
            
            # Store the widgets AND the original index to preserve the link to the variable's role
            self.y_axis_mapping_controls.append((name_edit, y_combo, x_combo, i))

        # Now, populate the grid using the clean list, ensuring no gaps
        for row_idx, (name_edit, y_combo, x_combo, _) in enumerate(self.y_axis_mapping_controls):
            y_axis_grid_layout.addWidget(name_edit, row_idx + 1, 0)
            y_axis_grid_layout.addWidget(y_combo, row_idx + 1, 1)
            y_axis_grid_layout.addWidget(x_combo, row_idx + 1, 2)
        
        # A separate, dedicated section for Fraction mapping
        fraction_group = QGroupBox("Fraction Mapping")
        fraction_layout = QFormLayout(fraction_group)
        self.fraction_x_combo = QComboBox()
        self.fraction_y_combo = QComboBox()
        fraction_layout.addRow("Fraction Position (X-Axis):", self.fraction_x_combo)
        fraction_layout.addRow("Fraction Label:", self.fraction_y_combo)
        self.fraction_mapping_widgets = (self.fraction_x_combo, self.fraction_y_combo)
        
        # Combine the grid and preview table
        preview_and_grid_layout = QHBoxLayout()
        preview_and_grid_layout.addLayout(y_axis_grid_layout, 1)
        self.preview_table = QTableWidget()
        preview_and_grid_layout.addWidget(self.preview_table, 1)
        
        mapping_main_layout.addLayout(preview_and_grid_layout)
        mapping_main_layout.addWidget(fraction_group)
        
        # --- MODIFICATION END ---

        self.profile_group = QGroupBox("3. Import Profiles")
        profile_layout = QGridLayout(self.profile_group)
        self.profile_combo = QComboBox()
        self.profile_combo.setPlaceholderText("Select a profile to load...")
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        self.profile_name_edit = QLineEdit()
        self.profile_name_edit.setPlaceholderText("Enter new profile name...")
        save_profile_btn = QPushButton("Save Current Mapping")
        delete_profile_btn = QPushButton("Delete Selected Profile")
        save_profile_btn.clicked.connect(self.save_profile)
        delete_profile_btn.clicked.connect(self.delete_profile)
        profile_layout.addWidget(QLabel("Load Profile:"), 0, 0)
        profile_layout.addWidget(self.profile_combo, 0, 1, 1, 2)
        profile_layout.addWidget(QLabel("Save As:"), 1, 0)
        profile_layout.addWidget(self.profile_name_edit, 1, 1)
        profile_layout.addWidget(save_profile_btn, 1, 2)
        profile_layout.addWidget(delete_profile_btn, 2, 1, 1, 2)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Import Data")
        self.button_box.accepted.connect(self.finish_import)
        self.button_box.rejected.connect(self.reject)

    def _hide_custom_widgets(self):
        self.custom_options_group.hide()
        self.mapping_group.hide()
        self.profile_group.hide()
        self.button_box.hide()
        self.setMinimumSize(600, 200)
        self.resize(600, 200)

    def _show_custom_widgets(self):
        self.custom_options_group.show()
        self.mapping_group.show()
        self.profile_group.show()
        self.button_box.show()
        self.setMinimumSize(950, 800)
        self.resize(950, 800)

    def browse_for_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", 
            "All Files (*.*);;Text Files (*.txt);;CSV Files (*.csv)")
        if filename:
            self.source_filename = filename
            self.filepath_edit.setText(filename)
            self.akta_btn.setEnabled(True)
            self.custom_btn.setEnabled(True)

    def _handle_akta_import(self):
        self.current_mode = 'akta'
        processed_data = self._process_akta_file_directly()
        if processed_data:
            QMessageBox.information(self, "Success", "ÄKTA file processed successfully.")
            
            # --- FIX: Create the correct mapping from default names to current custom names ---
            # This is the crucial step that links the importer's fixed logic to the user's settings.

            # 1. Get the original, default variable names in their fixed order.
            # This is our stable, internal reference.
            default_names = SettingsManager._get_default_plot_options()[9:20]
            
            # 2. The global `variable_name` list holds the current user-defined names
            #    in the corresponding order. This is what was used for the keys in `processed_data`.
            current_custom_names = variable_name

            # 3. Create a mapping from the default name to the custom name.
            # e.g., {'UV': 'Absorbance', 'pH': 'pH', ...}
            full_name_map = dict(zip(default_names, current_custom_names))
            
            # 4. Filter the map to include only the variables that were actually
            #    found and loaded in the processed data.
            final_name_mapping = {
                default_key: custom_key 
                for default_key, custom_key in full_name_map.items() 
                if custom_key in processed_data
            }
            
            # 5. Emit the data dictionary (which uses custom names as keys) and the
            #    new, correct mapping that allows the main window to find the data.
            self.data_imported.emit(processed_data, self.source_filename, final_name_mapping)
            
            self.accept()

    def _process_akta_file_directly(self):
        """
        Implementation of the user-provided parsing algorithm, corrected for API changes.
        """
        try:
            df = pd.read_csv(self.source_filename, encoding='utf-16', sep='\t', skiprows=1)
            # Rename columns based on Unicorn titles
            drops = []
            for x_1 in range(0,len(df.columns)):
                if "Unnamed" not in df.columns[x_1]:
                    df.iloc[0,x_1] = "ml." + df.columns[x_1]
                if "UV_CUT" in df.columns[x_1]:
                    drops = [x_1,x_1+1]
            
            if drops:
                df.drop(df.columns[drops], axis=1, inplace=True)

            # Initialize empty dataframes for all possible variables
            UV=pd.DataFrame(columns=["mL","unit"])
            Conductivity=pd.DataFrame(columns=["mL","unit"])
            Gradient_val=pd.DataFrame(columns=["mL","unit"])
            injection=pd.DataFrame(columns=["mL","unit"])
            pH=pd.DataFrame(columns=["mL","unit"])
            preC_press=pd.DataFrame(columns=["mL","unit"])
            sys_pres=pd.DataFrame(columns=["mL","unit"])
            sys_flow=pd.DataFrame(columns=["mL","unit"])
            fraction=pd.DataFrame(columns=["mL","unit"]) # Standardized columns
            
            # --- Main data extraction block ---
            df.columns = df.iloc[0]
            df = df[1:]
            
            try:
                UV=df[["ml.UV","mAU"]].apply(pd.to_numeric, errors='coerce').rename({"ml.UV":"mL","mAU":"unit"},axis=1)
                UV = UV.dropna(how='all')
            except (KeyError, IndexError): print("Warning: UV data not found.")

            try:
                pH=df[["ml.pH","pH"]].dropna().apply(pd.to_numeric, errors='coerce').rename({"ml.pH":"mL","pH":"unit"},axis=1)
                pH = pH.dropna(how='all')
            except (KeyError, IndexError): print("Warning: pH data not found.")
            
            try:
                Conductivity=df[["ml.Cond","mS/cm"]].dropna().apply(pd.to_numeric, errors='coerce').rename({"ml.Cond":"mL","mS/cm":"unit"},axis=1)
                Conductivity=Conductivity[(Conductivity>=0).all(1)]
            except (KeyError, IndexError): print("Warning: Conductivity data not found.")

            try:
                gval=df.columns.get_loc("ml.Conc B")
                # --- FIX: Removed redundant `axis=1` parameter ---
                Gradient_val=df.iloc[:,gval:gval+2].dropna().apply(pd.to_numeric, errors='coerce').rename(columns={df.columns[gval]:"mL",df.columns[gval+1]:"unit"})
                Gradient_val=Gradient_val[(Gradient_val>=0).all(1)]
            except (KeyError, IndexError): print("Warning: Gradient data not found.")

            try:
                fraction = df[["ml.Fraction","Fraction"]].dropna()
                fraction.columns = ["mL", "unit"]
                if not UV.empty:
                    # MODIFICATION: Use pd.concat for safer row addition.
                    start_row = pd.DataFrame([{'mL': 0, 'unit': '1'}])
                    waste_row = pd.DataFrame([{'mL': UV.iloc[-1]['mL'], 'unit': 'Waste'}])
                    fraction = pd.concat([start_row, fraction, waste_row], ignore_index=True)

                fraction["mL"]=fraction["mL"].apply(pd.to_numeric, errors='coerce')
                fraction = fraction.dropna(subset=['mL']).sort_values(by='mL').reset_index(drop=True)
            except (KeyError, IndexError): print("Warning: Fraction data not found.")

            try:
                pval=df.columns.get_loc("ml.PreC pressure")
                # --- FIX: Removed redundant `axis=1` parameter ---
                preC_press=df.iloc[:,pval:pval+2].dropna().apply(pd.to_numeric, errors='coerce').rename(columns={df.columns[pval]:"mL",df.columns[pval+1]:"unit"})
                preC_press=preC_press[(preC_press>=0).all(1)]
            except (KeyError, IndexError): print("Warning: Pre-Column Pressure data not found.")
            
            try:
                spval=df.columns.get_loc("ml.System pressure")
                # --- FIX: Removed redundant `axis=1` parameter ---
                sys_pres= df.iloc[:,spval:spval+2].dropna().apply(pd.to_numeric, errors='coerce').rename(columns={df.columns[spval]:"mL",df.columns[spval+1]:"unit"})
                sys_pres=sys_pres[(sys_pres>=0).all(1)]
            except (KeyError, IndexError): print("Warning: System Pressure data not found.")

            try:
                sys_flow= df[["ml.System flow","ml/min"]].dropna().apply(pd.to_numeric, errors='coerce').rename({"ml.System flow":"mL","ml/min":"unit"},axis=1)
                sys_flow=sys_flow[(sys_flow>=0).all(1)]
            except (KeyError, IndexError): print("Warning: System Flow data not found.")

            try:
                injection = df[["ml.Injection","Injection"]].dropna().apply(pd.to_numeric, errors='coerce').rename({"ml.Injection":"mL","Injection":"unit"},axis=1)
                injection=injection[(injection>=0).all(1)]
            except (KeyError, IndexError): print("Warning: Injection data not found.")

            final_df={
                variable_name[0]: UV, 
                variable_name[1]: pH,
                variable_name[2]: Conductivity, 
                variable_name[3]: sys_pres,
                variable_name[4]: Gradient_val, 
                variable_name[5]: sys_flow, 
                variable_name[6]: fraction,
                variable_name[7]: injection, 
                variable_name[8]: preC_press
                }

            final_df = {k: v for k, v in final_df.items() if not v.empty}

            if not final_df:
                QMessageBox.critical(self, "Import Error", "No data could be extracted. The file might be empty or have an unexpected format. Please try Custom Import.")
                return None
            return final_df

        except Exception as e:
            QMessageBox.critical(self, "ÄKTA Import Failed", f"An unexpected error occurred during processing:\n\n{e}\n\nPlease check the file format or use Custom Import.")
            return None

    def _handle_custom_import(self):
        self.current_mode = 'custom'
        self._show_custom_widgets()
        self.load_and_preview()

    def load_and_preview(self):
        if not self.source_filename or self.current_mode != 'custom': return
        self.raw_df, self.preview_df = None, None
        
        delimiter_map = {"Tab": "\t", "Comma": ",", "Space": r"\s+"}
        delimiter = delimiter_map[self.delimiter_combo.currentText()]
        header_row = self.header_spinbox.value()
        
        try:
            try:
                self.preview_df = pd.read_csv(self.source_filename, sep=delimiter, header=None, engine='python')
                self.raw_df = pd.read_csv(self.source_filename, sep=delimiter, header=header_row, engine='python')
            except UnicodeDecodeError:
                self.preview_df = pd.read_csv(self.source_filename, sep=delimiter, header=None, engine='python', encoding='utf-16')
                self.raw_df = pd.read_csv(self.source_filename, sep=delimiter, header=header_row, engine='python', encoding='utf-16')
        except Exception as e:
            QMessageBox.warning(self, "File Read Error", f"Could not parse file.\nError: {e}")
            self.raw_df = self.preview_df = None
        
        self.populate_mapping_combos()
        self.populate_preview()

    def populate_preview(self):
        self.preview_table.clear()
        df_to_show = self.preview_df if self.preview_raw_checkbox.isChecked() else self.raw_df
        if df_to_show is None: return

        df_subset = df_to_show.head(100)
        self.preview_table.setRowCount(df_subset.shape[0])
        self.preview_table.setColumnCount(df_subset.shape[1])
        headers = [str(h) for h in df_subset.columns]
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        for row in range(df_subset.shape[0]):
            for col in range(df_subset.shape[1]):
                item = QTableWidgetItem(str(df_subset.iat[row, col]))
                self.preview_table.setItem(row, col, item)
        self.preview_table.resizeColumnsToContents()

    def populate_mapping_combos(self):
        for _, y_combo, x_combo, _ in self.y_axis_mapping_controls:
            y_combo.clear(); x_combo.clear()
        
        self.fraction_x_combo.clear()
        self.fraction_y_combo.clear()

        if self.raw_df is None: return
        
        headers = self.raw_df.columns
        column_list = [f"Col {i}: {str(h)}" for i, h in enumerate(headers)]
        y_column_list = ["-- Not Mapped --"] + column_list
        
        for _, y_combo, x_combo, _ in self.y_axis_mapping_controls:
            y_combo.addItems(y_column_list)
            x_combo.addItems(column_list)
            
        self.fraction_x_combo.addItems(column_list)
        self.fraction_y_combo.addItems(y_column_list)

    def finish_import(self):
        if self.raw_df is None:
            QMessageBox.warning(self, "No Parsed Data", "Cannot import.")
            return

        final_df = {}
        name_mapping = {}
        
        # --- FIX: Get the true, unchangeable default names from SettingsManager ---
        # This list will be our stable, internal reference for mapping.
        default_names = SettingsManager._get_default_plot_options()[9:20]

        # Loop over the y-axis controls to map and process data.
        for name_edit, y_combo, x_combo, original_index in self.y_axis_mapping_controls:
            # The custom_name is what the user sees and what will be the key in the data dictionary.
            custom_name = name_edit.text().strip()
            
            if not custom_name or y_combo.currentText() == "-- Not Mapped --":
                continue
            if not x_combo.currentText():
                QMessageBox.critical(self, "Mapping Error", f"Variable '{custom_name}' has no X-axis selected.")
                return
            try:
                # --- FIX: Use the stable default_names list for the mapping key ---
                # This ensures the main UI can always find the data, e.g., via the internal key 'UV'.
                true_default_name = default_names[original_index]
                name_mapping[true_default_name] = custom_name

                y_col_idx = int(y_combo.currentText().split(':')[0].split(' ')[1])
                x_col_idx = int(x_combo.currentText().split(':')[0].split(' ')[1])
                
                subset_df = self.raw_df.iloc[:, [x_col_idx, y_col_idx]].copy()
                subset_df.columns = ["mL", "unit"]
                
                subset_df = subset_df.apply(pd.to_numeric, errors='coerce').dropna()
                
                if not subset_df.empty:
                    # Use the user-defined custom_name as the key for the actual data.
                    final_df[custom_name] = subset_df.sort_values(by="mL").reset_index(drop=True)
            except Exception as e:
                print(f"Warning processing '{custom_name}': {e}")
        
        # Process Fractions separately with the same robust mapping logic.
        frac_x_combo, frac_y_combo = self.fraction_mapping_widgets
        if frac_y_combo.currentText() != "-- Not Mapped --":
            try:
                x_col_idx = int(frac_x_combo.currentText().split(':')[0].split(' ')[1])
                y_col_idx = int(frac_y_combo.currentText().split(':')[0].split(' ')[1])

                subset_df = self.raw_df.iloc[:, [x_col_idx, y_col_idx]].copy()
                subset_df.columns = ["mL", "unit"]

                subset_df['mL'] = pd.to_numeric(subset_df['mL'], errors='coerce')
                subset_df['unit'] = subset_df['unit'].astype(str)
                subset_df = subset_df.dropna(subset=['mL'])
                
                if not subset_df.empty:
                    # --- FIX: Use the stable name for mapping, and the current name for data ---
                    custom_fraction_name = variable_name[6] # The current name (e.g., "Frac.")
                    true_default_fraction_name = default_names[6] # The internal name ('Fraction')
                    
                    final_df[custom_fraction_name] = subset_df.sort_values(by="mL").reset_index(drop=True)
                    name_mapping[true_default_fraction_name] = custom_fraction_name
            except Exception as e:
                print(f"Warning processing Fractions: {e}")

        if not final_df:
            QMessageBox.critical(self, "Import Error", "No data was successfully processed.")
            return
        
        self.data_imported.emit(final_df, self.source_filename, name_mapping)
        self.accept()

    def _load_profiles_to_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profiles = SettingsManager.get_import_profiles()
        if self.profiles:
            self.profile_combo.addItems(sorted(self.profiles.keys()))
        self.profile_combo.setCurrentIndex(-1)
        self.profile_combo.blockSignals(False)

    def _on_profile_selected(self):
        profile_name = self.profile_combo.currentText()
        if not profile_name or profile_name not in self.profiles: return

        self._handle_custom_import()

        profile_data = self.profiles[profile_name]
        parsing_opts = profile_data.get("parsing", {})
        
        self.delimiter_combo.setCurrentText(parsing_opts.get("delimiter", "Tab"))
        self.header_spinbox.setValue(parsing_opts.get("header_row", 0))

        if self.raw_df is not None:
            mapping_data = profile_data.get("mapping", {})
            
            # New format: a list of dictionaries
            if isinstance(mapping_data, list):
                for i, mapping_info in enumerate(mapping_data):
                    if i >= len(self.mapping_controls): break
                    name_edit, y_combo, x_combo = self.mapping_controls[i]
                    
                    fallback_name = variable_name[i] if i < len(variable_name) else f"Variable {i+1}"
                    
                    name_edit.setText(mapping_info.get("name", fallback_name))
                    y_combo.setCurrentText(mapping_info.get("y_col", "-- Not Mapped --"))
                    x_combo.setCurrentText(mapping_info.get("x_col", ""))
            
            # Backward compatibility for old format: a dictionary of dictionaries
            elif isinstance(mapping_data, dict):
                for i, (name_edit, y_combo, x_combo) in enumerate(self.mapping_controls):
                    if i >= len(variable_name): break
                    original_name = variable_name[i] # Key in old format
                    var_map = mapping_data.get(original_name, {})
                    name_edit.setText(original_name) # Old profiles don't have custom names
                    y_combo.setCurrentText(var_map.get("y_col", "-- Not Mapped --"))
                    x_combo.setCurrentText(var_map.get("x_col", ""))

        self.profile_name_edit.setText(profile_name)

    def save_profile(self):
        profile_name = self.profile_name_edit.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "No Name", "Please enter a name for the profile.")
            return
            
        settings = SettingsManager.load_settings()
        
        profile_data = {
            "parsing": {
                "import_mode": "custom",
                "delimiter": self.delimiter_combo.currentText(), 
                "header_row": self.header_spinbox.value(),
            },
            "mapping": [] # Now a list
        }
        for name_edit, y_combo, x_combo in self.mapping_controls:
            mapping_info = {
                "name": name_edit.text(),
                "y_col": y_combo.currentText(),
                "x_col": x_combo.currentText()
            }
            profile_data["mapping"].append(mapping_info)
            
        settings["import_profiles"][profile_name] = profile_data
        SettingsManager.save_settings(settings)
        
        QMessageBox.information(self, "Success", f"Profile '{profile_name}' saved.")
        self._load_profiles_to_combo()
        self.profile_combo.setCurrentText(profile_name)

    def delete_profile(self):
        profile_name = self.profile_combo.currentText()
        if not profile_name:
            QMessageBox.warning(self, "No Selection", "Please select a profile to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete profile '{profile_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            settings = SettingsManager.load_settings()
            if profile_name in settings["import_profiles"]:
                del settings["import_profiles"][profile_name]
                SettingsManager.save_settings(settings)
                QMessageBox.information(self, "Success", f"Profile '{profile_name}' deleted.")
                self._load_profiles_to_combo()
                self.profile_name_edit.clear()

class FractionLabelDialog(QDialog):
    """A dialog for editing and removing labels of collected fractions."""
    labels_updated = QtCore.Signal(pd.DataFrame)

    def __init__(self, fraction_df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Fraction Labels")
        self.setMinimumSize(550, 400)
        
        self.editable_df = fraction_df.copy().reset_index(drop=True)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel("Edit labels in the 'New Label' column or select rows to remove."))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Original Value", "Volume / Time", "New Label"])
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        
        main_layout.addWidget(self.table)
        self.repopulate_table()

        # MODIFICATION: Add layout for buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add New Fraction")
        remove_button = QPushButton("Remove Selected Fraction(s)")
        add_button.clicked.connect(self.add_fraction)
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        main_layout.addLayout(button_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_changes)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def add_fraction(self):
        """Opens a dialog to add a new fraction entry."""
        dialog = AddFractionDialog(self)
        if dialog.exec():
            pos_str, label_str = dialog.get_values()
            if pos_str and label_str:
                try:
                    pos_float = float(pos_str)
                    new_row = pd.DataFrame([{'mL': pos_float, 'unit': label_str, 'original_unit': 'User Added'}])
                    self.editable_df = pd.concat([self.editable_df, new_row], ignore_index=True)
                    # Sort by position and reset index to ensure data integrity
                    self.editable_df.sort_values(by='mL', inplace=True)
                    self.editable_df.reset_index(drop=True, inplace=True)
                    self.repopulate_table()
                except ValueError:
                    QMessageBox.warning(self, "Invalid Input", "Position must be a valid number.")

    def repopulate_table(self):
        """Clears and refills the table from the current state of self.editable_df."""
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.editable_df))
        
        for i, row in self.editable_df.iterrows():
            # Use 'unit' as the fallback if 'original_unit' doesn't exist
            original_label = str(row.get('original_unit', row['unit']))
            original_item = QTableWidgetItem(original_label)
            original_item.setFlags(original_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 0, original_item)
            
            vol_item = QTableWidgetItem(f"{row['mL']:.3f}")
            vol_item.setFlags(vol_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 1, vol_item)
            
            self.table.setItem(i, 2, QTableWidgetItem(str(row['unit'])))

        self.table.resizeColumnsToContents()

    def remove_selected(self):
        """Removes selected rows from the internal DataFrame and updates the table view."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        indices_to_remove = sorted([index.row() for index in selected_rows], reverse=True)
        
        self.editable_df.drop(indices_to_remove, inplace=True)
        self.editable_df.reset_index(drop=True, inplace=True)
        self.repopulate_table()

    def accept_changes(self):
        """Saves the latest labels from the table into the DataFrame and emits it."""
        # MODIFICATION: First, create a new list of all labels from the table.
        new_labels = []
        for i in range(self.table.rowCount()):
            new_label_item = self.table.item(i, 2)
            new_labels.append(new_label_item.text())
            
        # MODIFICATION: Then, assign the entire list to the DataFrame column in a single, robust operation.
        self.editable_df['unit'] = new_labels
        
        self.labels_updated.emit(self.editable_df)
        self.accept()

class Ui_SecondWindow(QDialog):
    """
    A modernized, self-contained dialog for editing plot options.
    It receives the current settings and emits a signal with the new settings.
    Handles an expanded list of 11 variables.
    """
    settings_saved = QtCore.Signal(list, bool)

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Options")
        self.setMinimumWidth(700)

        self.initial_settings = list(current_settings)
        self.original_variable_names = self.initial_settings[9:20]

        main_layout = QVBoxLayout(self)
        
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        self.create_styles_tab(tab_widget)
        self.create_variables_tab(tab_widget)
        self.create_general_tab(tab_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self.populate_fields()

    def create_styles_tab(self, tab_widget):
        styles_tab = QWidget()
        layout = QGridLayout(styles_tab)
        layout.setSpacing(15)
        
        self.color_combos = []
        self.style_combos = []
        self.plot_color_list = []

        for i in range(6):
            group_box = QGroupBox(f"Plot {i+1} Style")
            form_layout = QFormLayout(group_box)
            
            color_combo = QComboBox()
            color_combo.addItems(color_list)
            self.color_combos.append(color_combo)

            style_combo = QComboBox()
            style_combo.addItems(style_list)
            self.style_combos.append(style_combo)

            plot_color_style = QLineEdit()
            plot_color_style.setPlaceholderText("#RRGGBB")
            self.plot_color_list.append(plot_color_style)

            form_layout.addRow("Color:", color_combo)
            form_layout.addRow("Line Style:", style_combo)
            form_layout.addRow("Custom Color (Hex):", plot_color_style)
            
            row, col = i // 3, i % 3
            layout.addWidget(group_box, row, col)
            
        tab_widget.addTab(styles_tab, "Plot Styles")

    def create_variables_tab(self, tab_widget):
        variables_tab = QWidget()
        layout = QFormLayout(variables_tab)
        layout.setSpacing(10)
        
        group_box = QGroupBox("Variable Names and Units")
        group_layout = QFormLayout(group_box)
        group_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.variable_name_edits = []
        self.variable_unit_edits = []
        
        for i in range(11):
            name_edit = QLineEdit()
            unit_edit = QLineEdit()
            self.variable_name_edits.append(name_edit)
            self.variable_unit_edits.append(unit_edit)
            
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel("Unit:"))
            h_layout.addWidget(unit_edit)
            
            group_layout.addRow(f"Variable {i+1} Name:", name_edit)
            group_layout.addRow("", h_layout)

        layout.addWidget(group_box)
        tab_widget.addTab(variables_tab, "Variable Naming")

    def create_general_tab(self, tab_widget):
        general_tab = QWidget()
        layout = QVBoxLayout(general_tab)
        layout.setSpacing(15)

        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)
        self.font_combo = QComboBox()
        self.font_combo.addItems(['Arial', 'Helvetica', 'Times New Roman', 'serif', 'sans-serif'])
        self.font_size = QLineEdit()
        self.fraction_size = QLineEdit()
        font_layout.addRow("Font Family:", self.font_combo)
        font_layout.addRow("Font Size (pt):", self.font_size)
        font_layout.addRow("Fraction Label Size (pt):", self.fraction_size)
        
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        # MODIFICATION: Changed the checkbox label to be more generic and descriptive.
        self.offset_negative_cb = QCheckBox("Offset Primary Plot to Zero (if minimum is negative)")
        self.highlight_peak_cb = QCheckBox("Highlight Peaks on Primary Plot")
        self.show_relative_protein_cb = QCheckBox("Show Relative Protein Amount (Not Implemented)")
        options_layout.addWidget(self.offset_negative_cb)
        options_layout.addWidget(self.highlight_peak_cb)
        options_layout.addWidget(self.show_relative_protein_cb)

        layout.addWidget(font_group)
        layout.addWidget(options_group)
        layout.addStretch()
        
        tab_widget.addTab(general_tab, "General Settings")

    def populate_fields(self):
        """Fills all UI fields with values from the settings list."""
        settings = self.initial_settings
        for i in range(6):
            style, color_code = settings[i].split('@')
            self.style_combos[i].setCurrentText(style)
            color_map = {'b': 'blue', 'g': 'green', 'r': 'red', 'm': 'magenta', 'c': 'cyan', 'y': 'yellow'}
            if color_code in color_map:
                self.color_combos[i].setCurrentText(color_map[color_code])
                self.plot_color_list[i].clear()
            else:
                self.color_combos[i].setCurrentText("Custom")
                self.plot_color_list[i].setText(color_code)
        
        self.font_combo.setCurrentText(settings[6])
        self.font_size.setText(settings[7])
        self.fraction_size.setText(settings[8])

        for i in range(11):
            self.variable_name_edits[i].setText(settings[9 + i])
            self.variable_unit_edits[i].setText(settings[20 + i])
            
        self.offset_negative_cb.setChecked(settings[31] == 'True')
        self.highlight_peak_cb.setChecked(settings[32] == 'True')
        self.show_relative_protein_cb.setChecked(settings[33] == 'True')

    def collect_settings(self):
        """Gathers values from UI fields and returns a new settings list."""
        new_settings = [""] * len(self.initial_settings)
        
        for i in range(6):
            color = self.color_combos[i].currentText()
            style = self.style_combos[i].currentText()
            if color == 'Custom':
                color_code = self.plot_color_list[i].text()
            else:
                color_code = color[0]
            new_settings[i] = f"{style}@{color_code}"
            
        new_settings[6] = self.font_combo.currentText()
        new_settings[7] = self.font_size.text()
        new_settings[8] = self.fraction_size.text()

        for i in range(11):
            new_settings[9 + i] = self.variable_name_edits[i].text()
            new_settings[20 + i] = self.variable_unit_edits[i].text()

        new_settings[31] = str(self.offset_negative_cb.isChecked())
        new_settings[32] = str(self.highlight_peak_cb.isChecked())
        new_settings[33] = str(self.show_relative_protein_cb.isChecked())
        
        return new_settings

    def accept(self):
        """
        Overrides the default accept. It saves all settings EXCEPT for the variable names
        to the JSON file, but emits a signal with the current session's name changes
        so the main UI can update immediately.
        """
        new_settings = self.collect_settings()
        
        all_settings = SettingsManager.load_settings()
        all_settings["plot_options"] = new_settings
        SettingsManager.save_settings(all_settings)
        
        new_variable_names = new_settings[9:20]
        # MODIFICATION: Correctly compare the lists to determine if names have changed.
        names_changed = (new_variable_names != self.original_variable_names)
        
        self.settings_saved.emit(new_settings, names_changed)
        super().accept()

class ConcentrationCalculatorWindow(QDialog):
    """A simple dialog to calculate protein amount from a user-selected area."""
    def __init__(self, area, volume, start_vol, end_vol, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Protein Concentration Calculator")
        self.setMinimumWidth(400)

        self.area = area
        self.volume = volume

        main_layout = QVBoxLayout(self)

        results_group = QGroupBox("Selected Peak Data")
        results_layout = QFormLayout(results_group)
        
        self.range_label = QLabel(f"{start_vol:.2f} - {end_vol:.2f} mL")
        self.area_label = QLabel(f"{self.area:.2f} ml*mAU")
        self.volume_label = QLabel(f"{self.volume:.2f} mL")
        
        results_layout.addRow("Integration Range:", self.range_label)
        results_layout.addRow("Peak Area:", self.area_label)
        results_layout.addRow("Peak Volume:", self.volume_label)

        params_group = QGroupBox("Beer-Lambert Law Parameters")
        params_layout = QFormLayout(params_group)
        self.ext_coeff_input = QLineEdit("1.0")
        self.path_length_input = QLineEdit("1.0")
        self.mw_input = QLineEdit("1000")
        
        params_layout.addRow("Molar Ext. Coeff (M⁻¹cm⁻¹):", self.ext_coeff_input)
        params_layout.addRow("Path Length (cm):", self.path_length_input)
        params_layout.addRow("Molecular Weight (g/mol):", self.mw_input)
        
        self.ext_coeff_input.textChanged.connect(self.calculate_amount)
        self.path_length_input.textChanged.connect(self.calculate_amount)
        self.mw_input.textChanged.connect(self.calculate_amount)

        self.amount_output = QLineEdit("0.000")
        self.amount_output.setReadOnly(True)
        self.amount_output.setStyleSheet("font-weight: bold; background-color: #F0F3F4;")
        
        final_calc_layout = QFormLayout()
        final_calc_layout.addRow("Calculated Amount (mg):", self.amount_output)
        
        main_layout.addWidget(results_group)
        main_layout.addWidget(params_group)
        main_layout.addLayout(final_calc_layout)
        
        self.calculate_amount()

    def calculate_amount(self):
        """Reads inputs and calculates the final protein amount."""
        try:
            ext_coeff = float(self.ext_coeff_input.text())
            path_len = float(self.path_length_input.text())
            mw = float(self.mw_input.text())
            
            if ext_coeff == 0 or path_len == 0:
                self.amount_output.setText("N/A")
                return

            amount_mg = (self.area * mw) / (ext_coeff * path_len * 1000)
            self.amount_output.setText(f"{amount_mg:.3f}")

        except (ValueError, AttributeError):
            self.amount_output.setText("Invalid Input")


params = {'legend.fontsize': 'x-large',
          'figure.figsize': (15, 5),
         'axes.labelsize': 'x-large',
         'axes.titlesize':'x-large',
         'xtick.labelsize':'x-large',
         'ytick.labelsize':'x-large'}
pylab.rcParams.update(params)

# Global variables for plot state
init_val=0
fraction_var=0

class Ui_MainWindow(object):
    SLIDER_PRECISION_FACTOR = 1000
    
    def setupUi(self, MainWindow):
        """
        Sets up the entire UI for the main window, now with dynamic plot checkboxes
        and integrated session management buttons instead of a menubar.
        """
        MainWindow.setObjectName("MainWindow")
        MainWindow.setFixedSize(942, 820)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.source_filename = None
        self.data_file_load = None
        self.final_df = {}
        self.original_final_df = {}
        self.fraction_boundaries = []
        self.order_table = [] 
        
        self.plot_checkboxes = {}
        self.checkbox_name_order = [
            'UV', 'pH', 'Conductivity', 'Gradient', 'Flow rate', 
            'System Pressure', 'Pre-column Pressure', 'Fraction', 
            'Variable 1', 'Variable 2'
        ]
        self.name_to_index_map = {
            'UV': 0, 'pH': 1, 'Conductivity': 2, 'System Pressure': 3, 'Gradient': 4,
            'Flow rate': 5, 'Fraction': 6, 'Injection': 7, 'Pre-column Pressure': 8,
            'Variable 1': 9, 'Variable 2': 10
        }

        # Main layout structure
        main_v_layout = QVBoxLayout(self.centralwidget)
        self.tabWidget = QtWidgets.QTabWidget()
        main_v_layout.addWidget(self.tabWidget)
        
        self.tab1 = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab1, "Chromatogram Analyzer")
        tab1_layout = QVBoxLayout(self.tab1)
        
        self.scene = QtWidgets.QGraphicsScene()
        self.graphicsView = QtWidgets.QGraphicsView(self.scene)
        tab1_layout.addWidget(self.graphicsView, 1)

        controls_h_layout = QHBoxLayout()
        tab1_layout.addLayout(controls_h_layout)

        left_v_layout = QVBoxLayout()
        controls_h_layout.addLayout(left_v_layout, 2)

        plot_selection_group = QGroupBox("Plot Selection")
        self.plot_selection_layout = QGridLayout(plot_selection_group)
        left_v_layout.addWidget(plot_selection_group)

        for name in self.checkbox_name_order:
            checkbox = QtWidgets.QCheckBox(name)
            checkbox.setVisible(False)
            checkbox.stateChanged.connect(lambda state, cb=checkbox: self.check_clicked(cb))
            self.plot_checkboxes[name] = checkbox
        
        xaxis_group = QGroupBox("X-Axis Range")
        xaxis_layout = QGridLayout(xaxis_group)
        left_v_layout.addWidget(xaxis_group)

        self.xaxis_min = QLineEdit("X-axis Minimum"); self.xaxis_min.setReadOnly(True)
        self.ySlider = QSlider(QtCore.Qt.Horizontal); self.ySlider.setEnabled(False)
        self.yNumber = QLineEdit("0"); self.yNumber.setEnabled(False); self.yNumber.setFixedWidth(80)
        self.xaxis_max = QLineEdit("X-axis Maximum"); self.xaxis_max.setReadOnly(True)
        self.xSlider = QSlider(QtCore.Qt.Horizontal); self.xSlider.setEnabled(False)
        self.xNumber = QLineEdit("100"); self.xNumber.setEnabled(False); self.xNumber.setFixedWidth(80)
        xaxis_layout.addWidget(self.xaxis_min, 0, 0); xaxis_layout.addWidget(self.ySlider, 0, 1)
        xaxis_layout.addWidget(self.yNumber, 0, 2); xaxis_layout.addWidget(self.xaxis_max, 1, 0)
        xaxis_layout.addWidget(self.xSlider, 1, 1); xaxis_layout.addWidget(self.xNumber, 1, 2)
        
        right_v_layout = QVBoxLayout()
        controls_h_layout.addLayout(right_v_layout, 1)
        actions_group = QGroupBox("Actions")
        actions_layout = QGridLayout(actions_group)
        right_v_layout.addWidget(actions_group)
        
        # --- MODIFICATION: Button creation and renaming ---
        self.Open = QPushButton("Open Data File")
        self.LoadSession = QPushButton("Load Session")
        self.SaveSession = QPushButton("Save Session")
        self.Plot = QPushButton("Plot Data")
        self.Save_Image = QPushButton("Save Image")
        self.CalculateConc = QPushButton("Calculate Protein Conc.")
        self.PlotOpt = QPushButton("Plot Options")
        self.ResetZoom = QPushButton("Reset Zoom")
        self.Copy_Image = QPushButton("Copy Image")
        self.LabelFractions = QPushButton("Label Fractions")

        # --- MODIFICATION: Update which buttons are disabled at start ---
        # "Load Previous Session" should always be enabled. "Save Session" is disabled until data is loaded.
        buttons_to_disable = [self.Plot, self.Save_Image, self.Copy_Image, self.CalculateConc, self.ResetZoom, self.SaveSession]
        for btn in buttons_to_disable: btn.setEnabled(False)
        self.LabelFractions.setEnabled(True)

        # --- MODIFICATION: New button layout grid ---
        actions_layout.addWidget(self.Open, 0, 0, 1, 2)
        actions_layout.addWidget(self.LoadSession, 1, 0)
        actions_layout.addWidget(self.SaveSession, 1, 1)
        actions_layout.addWidget(self.Plot, 2, 0, 1, 2)
        actions_layout.addWidget(self.CalculateConc, 3, 0, 1, 2)
        actions_layout.addWidget(self.ResetZoom, 4, 0)
        actions_layout.addWidget(self.PlotOpt, 4, 1)
        actions_layout.addWidget(self.LabelFractions, 5, 0, 1, 2)
        actions_layout.addWidget(self.Save_Image, 6, 0)
        actions_layout.addWidget(self.Copy_Image, 6, 1)

        integration_group = QGroupBox("Integration Range Selection")
        integration_layout = QGridLayout(integration_group)
        left_v_layout.addWidget(integration_group)
        
        self.primary_variable_selector = QComboBox()
        self.primary_variable_selector.setEnabled(False)
        integration_layout.addWidget(QLabel("Primary Plot:"), 0, 0)
        integration_layout.addWidget(self.primary_variable_selector, 0, 1, 1, 2)
        
        self.start_slider = QSlider(QtCore.Qt.Horizontal)
        self.start_number = QLineEdit("0.0"); self.start_number.setFixedWidth(80)
        self.end_slider = QSlider(QtCore.Qt.Horizontal)
        self.end_number = QLineEdit("0.0"); self.end_number.setFixedWidth(80)
        integration_widgets = [self.start_slider, self.start_number, self.end_slider, self.end_number]
        for widget in integration_widgets: widget.setEnabled(False)
        integration_layout.addWidget(QLabel("Start:"), 1, 0); integration_layout.addWidget(self.start_slider, 1, 1)
        integration_layout.addWidget(self.start_number, 1, 2); integration_layout.addWidget(QLabel("End:"), 2, 0)
        integration_layout.addWidget(self.end_slider, 2, 1); integration_layout.addWidget(self.end_number, 2, 2)

        right_v_layout.addStretch()
        MainWindow.setCentralWidget(self.centralwidget)
        
        # --- MODIFICATION: Menubar and all related QActions have been removed ---
        # The MainWindow will no longer have a menubar.
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        
        # --- MODIFICATION: Update connections for new buttons and remove old ones ---
        self.Plot.clicked.connect(self.plot_graph)
        self.LabelFractions.clicked.connect(self.open_fraction_labeler)
        self.Open.clicked.connect(self.select_file)
        self.Save_Image.clicked.connect(self.save_image)
        self.Copy_Image.clicked.connect(self.copy_image_to_clipboard)
        self.LoadSession.clicked.connect(self.load_configuration) # New Connection
        self.SaveSession.clicked.connect(self.save_configuration) # New Connection
        self.ySlider.valueChanged.connect(self.slider_value_change)
        self.xSlider.valueChanged.connect(self.slider_value_change)
        self.xNumber.textChanged.connect(self.text_value_change)
        self.yNumber.textChanged.connect(self.text_value_change)
        self.PlotOpt.clicked.connect(self.open_plot_options)
        self.ResetZoom.clicked.connect(self.reset_zoom_view)
        self.start_slider.valueChanged.connect(self.start_slider_changed)
        self.end_slider.valueChanged.connect(self.end_slider_changed)
        self.start_number.editingFinished.connect(self.update_sliders_from_text)
        self.end_number.editingFinished.connect(self.update_sliders_from_text)
        self.CalculateConc.clicked.connect(self.open_concentration_calculator)
        self.primary_variable_selector.currentIndexChanged.connect(self._on_primary_variable_changed)
        
        # --- MODIFICATION: Add connections for dummy QActions used for help/about info. ---
        # We can still provide this info, perhaps via a help button in the future,
        # or just leave the methods available. For now, we'll keep the methods but remove triggers.
        # self.actionAbout.triggered.connect(self.license_info)
        # self.actionInstructions.triggered.connect(self.instruction_page)

        self.start_line = None
        self.end_line = None
        self.annot = None
        
        self.figure = Figure(figsize=[12, 6], dpi=65)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)

        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click_reset)
        
        self.selector = None
        self.is_zooming = False
        self.full_range_xmax = 0

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def setup_integration_sliders(self):
        """Configures integration sliders based on the selected Primary Plot."""
        fraction_key = variable_name[self.name_to_index_map['Fraction']]
        primary_data_key = self.primary_variable_selector.currentText()

        if self.plot_checkboxes['Fraction'].isChecked() and fraction_key in self.final_df and not self.final_df[fraction_key].empty:
            self.fraction_boundaries = self.final_df[fraction_key]['mL'].tolist()
            num_boundaries = len(self.fraction_boundaries)
            self.start_slider.setRange(0, num_boundaries - 1)
            self.end_slider.setRange(0, num_boundaries - 1)
            start_index = num_boundaries // 4
            end_index = (num_boundaries * 3) // 4
            if start_index >= end_index: end_index = start_index + 1 if start_index < num_boundaries - 1 else start_index
            self.start_slider.setValue(start_index)
            self.end_slider.setValue(end_index)
        elif primary_data_key and primary_data_key in self.final_df and not self.final_df[primary_data_key].empty:
            min_vol = self.final_df[primary_data_key]['mL'].min()
            max_vol = self.final_df[primary_data_key]['mL'].max()
            self.start_slider.setRange(int(min_vol * self.SLIDER_PRECISION_FACTOR), int(max_vol * self.SLIDER_PRECISION_FACTOR))
            self.end_slider.setRange(int(min_vol * self.SLIDER_PRECISION_FACTOR), int(max_vol * self.SLIDER_PRECISION_FACTOR))
            initial_start = int((min_vol + 0.25 * (max_vol - min_vol)) * self.SLIDER_PRECISION_FACTOR)
            initial_end = int((min_vol + 0.75 * (max_vol - min_vol)) * self.SLIDER_PRECISION_FACTOR)
            self.start_slider.setValue(initial_start)
            self.end_slider.setValue(initial_end)

        self.update_integration_lines()

    def copy_image_to_clipboard(self):
        """Saves the current figure to an in-memory buffer and copies it to the clipboard."""
        if not hasattr(self, 'figure') or not self.figure.get_axes():
            QMessageBox.warning(self.centralwidget, "No Figure", "Please plot a graph before copying.")
            return

        try:
            buf = io.BytesIO()
            self.figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            image = QtGui.QImage.fromData(buf.read())
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setImage(image)
            
            self.statusbar.showMessage("Image copied to clipboard.", 3000)
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Copy Error", f"Failed to copy the image.\nError: {e}")

    def save_configuration(self):
        """Saves the current chromatogram state, including data and UI settings, to a JSON file."""
        if not self.final_df:
            QMessageBox.warning(self.centralwidget, "No Data", "No data is loaded to save a configuration for.")
            return

        suggested_path = ""
        if self.source_filename:
            base, _ = os.path.splitext(self.source_filename)
            suggested_path = f"{base}_config.json"
        
        filePath, _ = QFileDialog.getSaveFileName(self.centralwidget, "Save Configuration", suggested_path, "JSON Config (*.json)")

        if not filePath:
            return

        try:
            final_df_json = {key: df.to_json(orient='split') for key, df in self.final_df.items()}
            plotted_variables = [cb.text() for cb in self.plot_checkboxes.values() if cb.isChecked() and cb.isVisible()]

            config_data = {
                "source_filename": self.source_filename,
                "final_df_json": final_df_json,
                "plotted_variables": plotted_variables,
                "x_axis_range": [self.ySlider.value(), self.xSlider.value()],
                "primary_variable": self.primary_variable_selector.currentText(),
            }

            with open(filePath, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            self.statusbar.showMessage(f"Configuration saved to {os.path.basename(filePath)}", 4000)

        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Save Error", f"Failed to save configuration.\nError: {e}")

    def load_configuration(self):
        """Loads a chromatogram state from a JSON configuration file."""
        filePath, _ = QFileDialog.getOpenFileName(self.centralwidget, "Load Configuration", "", "JSON Config (*.json)")

        if not filePath:
            return

        try:
            with open(filePath, 'r') as f:
                config_data = json.load(f)

            final_df_reconstructed = {key: pd.read_json(df_json, orient='split') for key, df_json in config_data["final_df_json"].items()}
            source_filename = config_data.get("source_filename", "Loaded from config")
            
            # Create a simple mapping of default names to the loaded names to reuse UI setup logic
            name_mapping = {}
            for loaded_name in final_df_reconstructed.keys():
                try:
                    idx = variable_name.index(loaded_name)
                    default_name = [k for k, v in self.name_to_index_map.items() if v == idx][0]
                    name_mapping[default_name] = loaded_name
                except (ValueError, IndexError):
                    print(f"Warning: Could not map loaded variable '{loaded_name}' to a default type.")

            self.on_data_imported(final_df_reconstructed, source_filename, name_mapping)
            
            # Set the checked state for plots
            plotted_variables = config_data.get("plotted_variables", [])
            self.order_table.clear()
            for cb in self.plot_checkboxes.values():
                cb.setChecked(cb.text() in plotted_variables)
            
            # Restore primary variable selection
            if primary_var := config_data.get("primary_variable"):
                self.primary_variable_selector.setCurrentText(primary_var)

            # Restore the X-axis zoom range
            if x_range := config_data.get("x_axis_range"):
                self.ySlider.blockSignals(True); self.xSlider.blockSignals(True)
                self.yNumber.blockSignals(True); self.xNumber.blockSignals(True)
                
                self.ySlider.setValue(x_range[0]); self.xSlider.setValue(x_range[1])
                self.yNumber.setText(str(x_range[0])); self.xNumber.setText(str(x_range[1]))
                
                self.ySlider.blockSignals(False); self.xSlider.blockSignals(False)
                self.yNumber.blockSignals(False); self.xNumber.blockSignals(False)

            self.plot_graph()
            self.statusbar.showMessage(f"Configuration loaded from {os.path.basename(filePath)}", 4000)

        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Load Error", f"Failed to load configuration.\nError: {e}")

    def open_fraction_labeler(self):
        """
        Opens the dialog to edit fraction labels. If no fraction data exists,
        it provides an empty table for the user to create it from scratch.
        """
        fraction_key = variable_name[self.name_to_index_map['Fraction']]
        
        # Check if fraction data already exists.
        if fraction_key in self.final_df and not self.final_df[fraction_key].empty:
            df_to_edit = self.final_df[fraction_key]
        else:
            # If not, create a new, empty DataFrame to serve as a blank slate.
            df_to_edit = pd.DataFrame(columns=['mL', 'unit'])
            
        dialog = FractionLabelDialog(df_to_edit, self.centralwidget)
        dialog.labels_updated.connect(self.apply_fraction_labels)
        dialog.exec()

    def apply_fraction_labels(self, updated_fraction_df):
        """
        Slot to receive the updated fraction data. This now handles both updating
        existing data and adding a new fraction data series to the application.
        """
        fraction_key = variable_name[self.name_to_index_map['Fraction']]
        
        # Add or update the fraction data in the main dictionary.
        self.final_df[fraction_key] = updated_fraction_df
        
        # If the user added fractions where none existed before, ensure the 'Fraction'
        # checkbox becomes visible so they can plot their new data.
        fraction_checkbox = self.plot_checkboxes.get('Fraction')
        if fraction_checkbox and not fraction_checkbox.isVisible():
            fraction_checkbox.setVisible(True)
            # Find the first empty spot in the grid layout to place the new checkbox.
            for i in range(self.plot_selection_layout.count(), 100):
                row = i // 4
                col = i % 4
                if self.plot_selection_layout.itemAtPosition(row, col) is None:
                    self.plot_selection_layout.addWidget(fraction_checkbox, row, col)
                    break
                    
        self.plot_graph()

    def on_zoom_select(self, eclick, erelease):
        """Callback for RectangleSelector."""
        x1, _ = eclick.xdata, eclick.ydata
        x2, _ = erelease.xdata, erelease.ydata

        if x1 is None or x2 is None: return

        xmin, xmax = min(x1, x2), max(x1, x2)
        if abs(xmax - xmin) < 0.1: return

        self.ySlider.blockSignals(True)
        self.xSlider.blockSignals(True)
        self.yNumber.blockSignals(True)
        self.xNumber.blockSignals(True)

        self.ySlider.setValue(int(round(xmin)))
        self.xSlider.setValue(int(round(xmax)))
        self.yNumber.setText(str(int(round(xmin))))
        self.xNumber.setText(str(int(round(xmax))))

        self.ySlider.blockSignals(False)
        self.xSlider.blockSignals(False)
        self.yNumber.blockSignals(False)
        self.xNumber.blockSignals(False)
        
        self.plot_graph()

    def reset_zoom_view(self):
        """Resets the plot view and UI controls to the full data range."""
        if self.full_range_xmax > 0:
            xmin, xmax = 0, self.full_range_xmax

            self.ySlider.blockSignals(True); self.xSlider.blockSignals(True)
            self.yNumber.blockSignals(True); self.xNumber.blockSignals(True)

            self.ySlider.setValue(int(round(xmin)))
            self.xSlider.setValue(int(round(xmax)))
            self.yNumber.setText(str(int(round(xmin))))
            self.xNumber.setText(str(int(round(xmax))))

            self.ySlider.blockSignals(False); self.xSlider.blockSignals(False)
            self.yNumber.blockSignals(False); self.xNumber.blockSignals(False)

            self.plot_graph()

    def on_mouse_click_reset(self, event):
        """ Resets zoom to the full range on right-click. """
        if event.button == 3 and event.inaxes:
            self.reset_zoom_view()

    def _apply_primary_plot_offset(self):
        """
        Applies or removes the negative offset based on the current settings.
        Always works from the original, unmodified data.
        """
        # First, restore the data to its original state to handle un-checking the box or changing the primary var.
        self.final_df = {k: v.copy() for k, v in self.original_final_df.items()}

        # If the setting is off, we are done. Data is restored to original.
        if output_options[31] != 'True':
            return

        primary_var_name = self.primary_variable_selector.currentText()
        if not primary_var_name or primary_var_name not in self.final_df:
            return

        df_to_offset = self.final_df[primary_var_name]
        if df_to_offset.empty:
            return
            
        min_val = df_to_offset['unit'].min()
        if min_val < 0:
            # Apply the offset by subtracting the negative minimum (which is equivalent to adding its absolute value)
            df_to_offset['unit'] = df_to_offset['unit'] - min_val

    def _on_primary_variable_changed(self):
        """
        Handler for when the user selects a new primary variable from the QComboBox.
        """
        if not self.original_final_df:  # Prevents firing during initial setup
            return
        
        # Apply offset logic based on the new selection and current settings
        self._apply_primary_plot_offset()
        
        # Re-configure the integration sliders for the new variable
        self.setup_integration_sliders()
        
        # Re-plot the graph to reflect the changes
        self.plot_graph()

    def apply_new_settings(self, new_settings, names_changed):
        """
        Slot to receive and apply settings from the Plot Options dialog.
        """
        global output_options, variable_name, variable_unit, units # order_table is no longer global
        
        old_variable_names = list(variable_name)
        
        output_options = new_settings
        variable_name = output_options[9:20]
        variable_unit = output_options[20:31]
        units = {name: variable_unit[i] for i, name in enumerate(variable_name)}

        for default_name, checkbox in self.plot_checkboxes.items():
            idx = self.name_to_index_map.get(default_name)
            if idx is not None and idx < len(variable_name):
                checkbox.setText(variable_name[idx])
        
        if names_changed and self.final_df:
            old_to_new_map = dict(zip(old_variable_names, variable_name))
            
            self.final_df = {old_to_new_map.get(k, k): v for k, v in self.final_df.items()}
            self.original_final_df = {old_to_new_map.get(k, k): v for k, v in self.original_final_df.items()}
            
            current_selection = self.primary_variable_selector.currentText()
            new_selection = old_to_new_map.get(current_selection, current_selection)
            self.primary_variable_selector.blockSignals(True)
            self.primary_variable_selector.clear()
            self.primary_variable_selector.addItems(self.final_df.keys())
            self.primary_variable_selector.setCurrentText(new_selection)
            self.primary_variable_selector.blockSignals(False)

        self.order_table.clear()
        for default_key in self.checkbox_name_order:
            if default_key in self.plot_checkboxes:
                checkbox = self.plot_checkboxes[default_key]
                if checkbox.isChecked() and checkbox.isVisible():
                    self.order_table.append(checkbox.text())
        
        self._apply_primary_plot_offset()
        if self.final_df:
            self.plot_graph()

    def retranslateUi(self, MainWindow):
        """
        Updates all static text in the UI. Crucially, this NO LONGER sets checkbox text.
        """
        MainWindow.setWindowTitle("AKTA Chromatogram Analyzer V4.00")
        # --- FIX: REMOVED all self.UV.setText, self.pH.setText, etc. ---
        # The checkbox text is now managed exclusively by update_variable_data.
        self.Open.setText("Open")
        self.Plot.setText("Plot")
        self.Save_Image.setText("Save Image")
        self.xaxis_max.setText("X-axis Maximum")
        self.xaxis_min.setText("X-axis Minimum")
        #self.menuFile.setTitle("File")
        #self.menuAbout_Info.setTitle("Information")
        self.PlotOpt.setText("Plot Options")
        self.ResetZoom.setText("Reset Zoom")
        self.CalculateConc.setText("Calculate Protein Conc.")

    def update_integration_lines(self):
        """Updates the line edit text and the vertical lines on the plot."""
        start_val, end_val = 0.0, 0.0

        if self.plot_checkboxes['Fraction'].isChecked() and self.fraction_boundaries:
            start_index, end_index = self.start_slider.value(), self.end_slider.value()
            if 0 <= start_index < len(self.fraction_boundaries):
                start_val = self.fraction_boundaries[start_index]
            if 0 <= end_index < len(self.fraction_boundaries):
                end_val = self.fraction_boundaries[end_index]
        else:
            start_val = self.start_slider.value() / float(self.SLIDER_PRECISION_FACTOR)
            end_val = self.end_slider.value() / float(self.SLIDER_PRECISION_FACTOR)
        
        self.start_number.setText(f"{start_val:.3f}")
        self.end_number.setText(f"{end_val:.3f}")

        if self.start_line and self.end_line:
            self.start_line.set_xdata([start_val, start_val])
            self.end_line.set_xdata([end_val, end_val])
            self.canvas.draw_idle()

    def update_sliders_from_text(self):
        """Updates sliders when the user types a value in the line edits."""
        try:
            start_val, end_val = float(self.start_number.text()), float(self.end_number.text())
            
            self.start_slider.blockSignals(True)
            self.end_slider.blockSignals(True)

            if self.plot_checkboxes['Fraction'].isChecked() and self.fraction_boundaries:
                boundaries = np.array(self.fraction_boundaries)
                start_index = np.argmin(np.abs(boundaries - start_val))
                end_index = np.argmin(np.abs(boundaries - end_val))
                self.start_slider.setValue(start_index)
                self.end_slider.setValue(end_index)
            else:
                self.start_slider.setValue(int(start_val * self.SLIDER_PRECISION_FACTOR))
                self.end_slider.setValue(int(end_val * self.SLIDER_PRECISION_FACTOR))

            self.start_slider.blockSignals(False)
            self.end_slider.blockSignals(False)
            
            self.update_integration_lines()
        except ValueError:
            self.update_integration_lines()

    def open_concentration_calculator(self):
        """Calculates area for the selected Primary Plot and opens the calculator."""
        primary_curve_name = self.primary_variable_selector.currentText()

        if not primary_curve_name or primary_curve_name not in self.final_df:
            QMessageBox.warning(self.centralwidget, "No Data", "Please select a Primary Plot from the dropdown menu before calculating concentration.")
            return

        primary_data = self.final_df[primary_curve_name]
        start_vol, end_vol = float(self.start_number.text()), float(self.end_number.text())

        if start_vol >= end_vol:
            QMessageBox.warning(self.centralwidget, "Invalid Range", "The integration start volume must be less than the end volume.")
            return
            
        integration_slice = primary_data[(primary_data['mL'] >= start_vol) & (primary_data['mL'] <= end_vol)]
        
        if integration_slice.empty:
            QMessageBox.warning(self.centralwidget, "Empty Slice", "No data points found in the selected integration range.")
            return

        area = np.trapezoid(integration_slice['unit'], integration_slice['mL'])
        volume = end_vol - start_vol

        self.calc_dialog = ConcentrationCalculatorWindow(area, volume, start_vol, end_vol, self.centralwidget)
        self.calc_dialog.show()

    def start_slider_changed(self):
        """Slot for when the START slider is moved."""
        start_val, end_val = self.start_slider.value(), self.end_slider.value()
        if start_val >= end_val:
            self.end_slider.blockSignals(True)
            self.end_slider.setValue(start_val + 1)
            self.end_slider.blockSignals(False)
        self.update_integration_lines()

    def end_slider_changed(self):
        """Slot for when the END slider is moved."""
        start_val, end_val = self.start_slider.value(), self.end_slider.value()
        if end_val <= start_val:
            self.start_slider.blockSignals(True)
            self.start_slider.setValue(end_val - 1)
            self.start_slider.blockSignals(False)
        self.update_integration_lines()
        
    def check_clicked(self, checkbox):
        global fraction_var, init_val # order_table is no longer global
        text = checkbox.text()
        is_checked = checkbox.isChecked()

        default_key = next((key for key, cb_widget in self.plot_checkboxes.items() if cb_widget is checkbox), None)

        if default_key == 'Fraction':
            fraction_var = 1 if is_checked else 0
            init_val = 0
            self.setup_integration_sliders()
        else:
            if is_checked and text not in self.order_table:
                self.order_table.append(text)
            elif not is_checked and text in self.order_table:
                self.order_table.remove(text)

    def update_variable_data(self):       
        """
        Updates global variables and re-translates UI text for variables.
        """
        global variable_name, variable_unit, units
        variable_name = output_options[9:20]
        variable_unit = output_options[20:31]
        units = dict([[y, variable_unit[x]] for x, y in enumerate(variable_name)]) 
        
        # Update the text of the actual checkbox widgets
        for default_name, checkbox in self.plot_checkboxes.items():
            idx = self.name_to_index_map.get(default_name)
            if idx is not None and idx < len(variable_name):
                checkbox.setText(variable_name[idx])
        
        self.retranslateUi(MainWindow)

    def slider_value_change(self):
        val_min, val_max = self.ySlider.value(), self.xSlider.value()
        self.xNumber.setText(str(val_max))
        self.yNumber.setText(str(val_min))
        
    def text_value_change(self):
        try:
            val_min, val_max = int(self.yNumber.text()), int(self.xNumber.text())
        except ValueError:
            val_min, val_max = 0, 0
        self.ySlider.setValue(val_min)
        self.xSlider.setValue(val_max)
        
    def plot_graph(self):
        def autoscale_y(ax, y_margin=0.1):
            """Robustly autoscale the y-axis for data within the current x-limits."""
            view_ymin, view_ymax = float('inf'), float('-inf')
            for line in ax.get_lines():
                x_data, y_data = line.get_xdata(), np.asarray(line.get_ydata())
                x_min, x_max = ax.get_xlim()
                y_displayed = y_data[(x_data >= x_min) & (x_data <= x_max)]
                
                if y_displayed.size > 0:
                    view_ymin = min(view_ymin, y_displayed.min())
                    view_ymax = max(view_ymax, y_displayed.max())
            
            if view_ymin == float('inf'): return None, None
            
            y_range = view_ymax - view_ymin
            y_range = abs(view_ymax * 0.1) if y_range == 0 else y_range
            
            final_ymin = 0 if view_ymin < 0 else view_ymin - y_margin * y_range
            final_ymax = view_ymax + y_margin * y_range
            
            return final_ymin, final_ymax

        self.figure.clear()
        
        global init_val, xmin_val, xmax_val, save_figure, fraction_var
        num_graphs = len(self.order_table)

        fraction_key = variable_name[self.name_to_index_map['Fraction']]
        
        if not self.final_df or not self.order_table:
            self.canvas.draw() # Draw an empty canvas if there's nothing to plot
            return
            
        primary_data_key = self.order_table[0]
        if primary_data_key not in self.final_df or self.final_df[primary_data_key].empty:
            QMessageBox.critical(self.centralwidget, "Plotting Error", f"The data for '{primary_data_key}' is missing or empty.")
            return

        if init_val == 0:
            # Find the min/max across all selected data series for a robust initial zoom
            all_min = []
            all_max = []
            for key in self.order_table:
                if key in self.final_df and not self.final_df[key].empty:
                    all_min.append(self.final_df[key]['mL'].min())
                    all_max.append(self.final_df[key]['mL'].max())
            
            xmin_val = min(all_min) if all_min else 0
            xmax_val = max(all_max) if all_max else 100

            self.full_range_xmax = xmax_val
            init_val = 1
            self.ySlider.setRange(int(xmin_val), int(xmax_val))
            self.xSlider.setRange(int(xmin_val), int(xmax_val))
            self.ySlider.setValue(int(xmin_val))
            self.xSlider.setValue(int(xmax_val))
        else:
            xmin_val, xmax_val = float(self.ySlider.value()), float(self.xSlider.value())
        
        self.xNumber.setText(str(round(xmax_val)))
        self.yNumber.setText(str(round(xmin_val)))
        self.setup_integration_sliders()
        
        if num_graphs > 0:
            ax0 = self.figure.add_subplot(111)
            ax0.set_xlabel("Volume (mL)")
            self.annot = ax0.annotate("", xy=(0, 0), xytext=(20, 20),
                                      textcoords="offset points",
                                      bbox=dict(boxstyle="round", fc="wheat", alpha=0.9),
                                      arrowprops=dict(arrowstyle="->"))
            self.annot.set_visible(False)
            
            axes = [ax0]
            for i in range(min(num_graphs, 6)):
                current_ax = axes[-1]
                if i >= len(self.order_table): continue
                data_key = self.order_table[i]
                
                if data_key not in self.final_df: continue

                p, = current_ax.plot(self.final_df[data_key]['mL'], self.final_df[data_key]['unit'],
                                     ls=output_options[i].split("@")[0], color=output_options[i].split("@")[1],
                                     picker=5)
                current_ax.set_ylabel(data_key + units.get(data_key, ''))
                current_ax.yaxis.label.set_color(p.get_color())
                current_ax.tick_params(axis='y', colors=p.get_color())
                
                if i < num_graphs - 1 and i < 5:
                    new_ax = ax0.twinx()
                    new_ax.spines.right.set_position(("axes", 1.0 + i * 0.12))
                    axes.append(new_ax)

            if num_graphs > 6:
                QMessageBox.information(self.centralwidget, "Plotting Limitation", "Cannot plot more than 6 plots at a time!")

            start_pos, end_pos = float(self.start_number.text()), float(self.end_number.text())
            self.start_line = ax0.axvline(x=start_pos, color='r', linestyle='--', linewidth=1.5)
            self.end_line = ax0.axvline(x=end_pos, color='r', linestyle='--', linewidth=1.5)

            primary_plot_for_peaks = self.primary_variable_selector.currentText()
            if output_options[32] == 'True' and primary_plot_for_peaks in self.final_df:
                peak_indices, _ = signal.find_peaks(self.final_df[primary_plot_for_peaks]['unit'], prominence=10, distance=10)
                ax0.plot(self.final_df[primary_plot_for_peaks]['mL'].iloc[peak_indices], 
                         self.final_df[primary_plot_for_peaks]['unit'].iloc[peak_indices], 
                         "*", color=ax0.get_lines()[0].get_color(), markersize=10)

        layout_params = {'left': 0.1, 'right': 0.9, 'top': 0.95, 'bottom': 0.15}
        if num_graphs == 3: layout_params['right'] = 0.85
        elif num_graphs == 4: layout_params['right'] = 0.78
        elif num_graphs == 5: layout_params['right'] = 0.71
        elif num_graphs >= 6: layout_params['right'] = 0.64
        
        if fraction_var == 1 and fraction_key in self.final_df and 'ax0' in locals():
            layout_params['bottom'] = 0.35 
            ax6 = ax0.twiny()
            ax6.set_xlabel("Fractions")
            
            temp_tick_labels = self.final_df[fraction_key]['unit'].tolist()
            temp_tick_sets = self.final_df[fraction_key]['mL'].tolist()
            
            visible_ticks = [(ts, str(tl)) for ts, tl in zip(temp_tick_sets, temp_tick_labels) if xmin_val <= ts <= xmax_val]
            
            if visible_ticks:
                tick_sets, tick_labels = zip(*visible_ticks)
                
                ax6.set_xticks(tick_sets)
                ax6.set_xticklabels(tick_labels, rotation=0, fontsize=fraction_lbl_size_main)
                ax6.spines["bottom"].set_position(("axes", -0.30)) 
                ax6.xaxis.set_ticks_position("bottom")
                ax6.xaxis.set_label_position("bottom")
                for tick_pos in tick_sets:
                    ax6.axvline(tick_pos, 0, 1, alpha=0.2, color='k', linewidth='1', ls='--')
            else:
                ax6.set_xticks([])
                ax6.set_xticklabels([])

        self.figure.subplots_adjust(**layout_params)
        
        if 'ax0' in locals():
            all_axes = self.figure.get_axes()
            for ax in all_axes:
                ax.set_xlim(left=xmin_val, right=xmax_val)
                # MODIFICATION: The check for the "Fractions" axis now also controls minor ticks.
                if ax.get_xlabel() != "Fractions":
                    y_min, y_max = autoscale_y(ax)
                    if y_min is not None:
                        ax.set_ylim(bottom=y_min, top=y_max)
                    # Minor ticks are now only turned on for non-fraction axes.
                    ax.minorticks_on()
            
            self.selector = RectangleSelector(ax0, self.on_zoom_select, useblit=False, button=[1], 
                                              props=dict(facecolor='none', edgecolor='black', lw=1.5, ls='--'))

        save_figure = self.figure
        self.update_integration_lines()
        self.canvas.draw()

    def on_hover(self, event):
        """
        Callback for mouse motion. Shows an annotation with the exact data point
        values for ALL visible plots at the cursor's X-position. The annotation
        box automatically repositions itself to avoid being clipped by the plot edges.
        """
        # If the annotation object doesn't exist or the cursor is outside the plot area, hide it.
        if not hasattr(self, 'annot') or self.annot is None or event.inaxes is None:
            if hasattr(self, 'annot') and self.annot and self.annot.get_visible():
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return

        # Get the primary axis, where the annotation lives.
        primary_ax = self.annot.axes
        
        # If there are no lines plotted, there's nothing to do.
        if not primary_ax.lines:
            return
            
        # The first line on the primary axis will be our reference for the arrow position.
        primary_line = primary_ax.lines[0]
        x_ref, y_ref = primary_line.get_data()
        
        if len(x_ref) == 0:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return

        # --- 1. Position the Annotation Arrow ---
        # Find the Y-value on the primary line corresponding to the mouse's X-position.
        target_x = event.xdata
        anchor_y = np.interp(target_x, x_ref, y_ref)
        self.annot.xy = (target_x, anchor_y)

        # --- 2. Build the Annotation Text from All Plots ---
        text_parts = [f"Volume: {target_x:.3f}"]

        for ax in self.figure.get_axes():
            if ax.get_xlabel() == "Fractions": continue
            
            for line in ax.get_lines():
                if not line.get_visible() or line.get_picker() is None: continue

                xdata, ydata = line.get_data()
                if len(xdata) == 0: continue
                
                idx = np.argmin(np.abs(xdata - target_x))
                y_point = ydata[idx]

                y_label_text = ax.get_ylabel().split('(')[0].strip()
                text_parts.append(f"{y_label_text}: {y_point:.3f}")
        
        # --- 3. Dynamically Position the Annotation Box ---
        xmin, xmax = primary_ax.get_xlim()
        ymin, ymax = primary_ax.get_ylim()

        # Check if the anchor point is in the top 30% of the Y-axis
        is_near_top = anchor_y > (ymin + 0.7 * (ymax - ymin))
        # Check if the anchor point is in the rightmost 20% of the X-axis
        is_near_right = target_x > (xmin + 0.8 * (xmax - xmin))

        # Estimate box dimensions in pixels for accurate placement
        num_lines = len(text_parts)
        box_height_estimate = num_lines * 15 
        box_width_estimate = 140 # Generous estimate for text like "Conductivity: 134.067"

        # Set default horizontal offset (pixels)
        horizontal_offset = 20
        if is_near_right:
            # If near the right edge, move the box to the left of the cursor
            horizontal_offset = -(box_width_estimate + 20)

        # Set default vertical offset (pixels)
        vertical_offset = 20
        if is_near_top:
            # If near the top, move the box down by its height plus some padding
            vertical_offset = -(box_height_estimate + 20)

        # Apply the new calculated offset. This works because we set `textcoords="offset points"`
        # when the annotation was first created in the `plot_graph` method.
        self.annot.set_position((horizontal_offset, vertical_offset))
        
        # --- 4. Display the Annotation ---
        if len(text_parts) > 1: # Only show if we found at least one data line
            self.annot.set_text("\n".join(text_parts))
            self.annot.set_visible(True)
        else:
            self.annot.set_visible(False)
        
        self.canvas.draw_idle()

    def select_file(self):
        """Launches the Import Wizard to select and process a data file."""
        wizard = ImportWizard(self.centralwidget)
        wizard.data_imported.connect(self.on_data_imported)
        wizard.exec()

    def on_data_imported(self, processed_data, source_filename, name_mapping):
        """
        Receives data, populates UI controls, and triggers the first plot.
        All plot selection checkboxes are now unchecked by default on load.
        """
        global init_val
        self.original_final_df = {k: v.copy() for k, v in processed_data.items()}
        self.final_df = processed_data
        self.source_filename = source_filename
        
        self.order_table.clear()

        controls_to_enable = [self.Plot, self.Save_Image, self.Copy_Image, self.CalculateConc, 
                              self.ResetZoom, self.ySlider, self.xSlider, self.yNumber, self.xNumber,
                              self.start_slider, self.start_number, self.end_slider, self.end_number,
                              self.primary_variable_selector, self.SaveSession]
        for control in controls_to_enable: control.setEnabled(True)
        
        while self.plot_selection_layout.count():
            item = self.plot_selection_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.setParent(None)
        
        widgets_to_display = []
        for default_name in self.checkbox_name_order:
            if default_name == 'Fraction': continue
            if default_name in name_mapping and name_mapping[default_name] in self.final_df:
                custom_name = name_mapping[default_name]
                checkbox = self.plot_checkboxes[default_name]
                checkbox.setText(custom_name)
                
                # MODIFICATION: Ensure all checkboxes are unchecked by default.
                checkbox.setChecked(False)
                
                widgets_to_display.append(checkbox)

        if 'Fraction' in name_mapping and name_mapping['Fraction'] in self.final_df:
            checkbox = self.plot_checkboxes['Fraction']
            checkbox.setText(name_mapping['Fraction'])
            checkbox.setChecked(False)
            widgets_to_display.append(checkbox)

        for i, widget in enumerate(widgets_to_display):
            widget.setVisible(True)
            self.plot_selection_layout.addWidget(widget, i // 4, i % 4)

        self.primary_variable_selector.blockSignals(True)
        self.primary_variable_selector.clear()
        primary_options = [name for name in self.final_df if 'fraction' not in name.lower()]
        self.primary_variable_selector.addItems(primary_options)
        
        uv_key_found = next((key for key in primary_options if 'uv' in key.lower()), None)
        if uv_key_found:
            self.primary_variable_selector.setCurrentText(uv_key_found)
        self.primary_variable_selector.blockSignals(False)

        self._apply_primary_plot_offset() # Apply offset even if nothing is plotted yet
        init_val = 0
        self.plot_graph() # This will now correctly draw a blank plot
        
    def save_image(self):
        global save_figure
        if not hasattr(self, 'figure') or not self.figure.get_axes():
            QMessageBox.warning(self.centralwidget, "No Figure", "Please plot a graph before saving.")
            return

        suggested_path = ""
        if self.source_filename:
            base, _ = os.path.splitext(self.source_filename)
            suggested_path = f"{base}_chromatogram.png"

        filters = "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;JPEG (*.jpg)"
        filePath, _ = QFileDialog.getSaveFileName(self.centralwidget, "Save Image", suggested_path, filters)

        if filePath:
            try:
                save_figure.savefig(filePath, dpi=300, bbox_inches='tight')
            except Exception as e:
                QMessageBox.critical(self.centralwidget, "Save Error", f"Failed to save the image.\nError: {e}")  

    def license_info(self):
        msg=QMessageBox(QMessageBox.Information,"Developer Information", "Software developed by Anindya Karmaker. Checkout the <a href='https://github.com/Anindya-Karmaker/Chromatogram-and-Glycan-Analyzer/'>GitHub</a> link for more updates.  Disclaimer: The software cannot guarantee the accuracy of the data and the developer claims no responsiblity. Please verify the data before publishing the output data from this software.")
        msg.exec()

    def instruction_page(self):
        msg=QMessageBox(QMessageBox.Information,"Instructions", "The software can read the txt/csv output file from the Unicorn software or other software or platform generated chromatograms. Tested with Unicorn v7.0. On the Unicorn Software, select all of the data that you want to export and the output will be a text file. Load the text file into the software. Press the plot button and the checked graphs will appear magically. Choose the graphs that you are interested by checking the check-boxes and press plot. You can zoom in the graph by choosing the X-axis maximum and minimum values. To see the fractions, check the fraction check-box. Fractions check-box will reset the x-axis minimum and maximum. The export data option will export the data in Excel format and the save image option will save the image graph at 300 DPI for direct use.")
        msg.exec()

    def save_data(self):
        if self.data_file_load is None or self.data_file_load.empty:
            QMessageBox.warning(self.centralwidget, "No Data", "There is no processed data to export.")
            return

        suggested_path = ""
        if self.source_filename:
            base, _ = os.path.splitext(self.source_filename)
            suggested_path = f"{base}_data.xlsx"

        filters = "Excel Workbook (*.xlsx);;CSV (*.csv)"
        filePath, selectedFilter = QFileDialog.getSaveFileName(self.centralwidget, "Export Data", suggested_path, filters)

        if filePath:
            try:
                if filePath.endswith('.xlsx'):
                    self.data_file_load.to_excel(filePath, index=False)
                else:
                    self.data_file_load.to_csv(filePath, index=False)
            except Exception as e:
                QMessageBox.critical(self.centralwidget, "Export Error", f"Failed to export the data.\nError: {e}")
            
    def open_plot_options(self):
        dialog = Ui_SecondWindow(output_options, self.centralwidget)
        dialog.settings_saved.connect(self.apply_new_settings)
        dialog.exec()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())