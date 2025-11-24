# Advanced Chromatogram Analyzer

A powerful, browser-based tool for visualizing, analyzing, and exporting chromatography data directly from ÄKTA-generated files or custom CSV/Excel sheets. No installation required.

<img width="1611" height="1019" alt="image" src="https://github.com/user-attachments/assets/1830c5ba-40cd-4891-ab19-cd5107d0f239" />

## 🧬 Overview

This tool was created for researchers who need a fast, private, and flexible way to analyze chromatography data without being tied to proprietary software. It runs entirely in your web browser, meaning your experimental data never leaves your computer. It's designed to be intuitive for daily lab use while providing powerful features for in-depth analysis and generating publication-ready figures.

## 🚀 Key Features

-   **Smart Data Import:**
    -   **ÄKTA Native Support:** Parses tab-delimited `.txt` or `.csv` files from GE Unicorn software, automatically extracting units and variable names.
    -   **Baseline Correction:** Automatically detects negative UV values upon import and offers to offset the baseline to zero.
    -   **Custom Import Wizard:** Map columns from generic CSV or Excel (`.xlsx`, `.xls`) files.
-   **Session Management:** Save your entire analysis state—including data, annotations, integration bounds, and visual settings—into a single `.json` file to resume work later.
-   **Interactive Multi-Axis Plotting:**
    -   Visualize multiple variables on a single plot with synchronized axes.
    -   **Auto-scaling Baseline:** The "UV (Baseline Corrected)" axis automatically synchronizes with the main UV axis for accurate comparison.
    -   Full control over line color, thickness, style, and labels.
-   **Advanced Peak Analysis & Integration:**
    -   **Net Area Calculation:** Toggle **"Use UV-Baseline Corrected Data"** to calculate the area *between* the raw UV signal and the baseline signal.
    -   **Visual Integration:** Toggle **"Show Region"** to visually shade the specific area being integrated with customizable colors.
    -   Automatically calculates **Peak Area**, **Volume**, **Asymmetry Factor (As)**, and **HETP**.
-   **Rich Annotations:**
    -   **Fraction Management:** Automatically import or manually add/edit fraction markers.
    -   **Label Regions:** Highlight specific phases (e.g., "Load", "Elution") with colored background regions.
-   **Protein Concentration Calculator:** Uses the integrated net peak area and Beer-Lambert law parameters to estimate total protein amount (mg).
-   **Publication-Ready Styling:**
    -   **Professional Axis Styling:** Enable and customize **Minor Ticks** for both X and Y axes.
    -   **High-Res Export:** Save plots as PNGs at up to 3x resolution.
    -   **Fine-Grained Control:** Adjust font sizes, line heights, legend positions, and label rotation via a dedicated settings panel.
-   **100% Client-Side:** Your data is processed locally in your browser. Nothing is ever uploaded to a server, ensuring complete data privacy.

## ⚙️ How to Use

No installation is needed!

1.  **Visit the Live Tool:** [https://anindya-karmaker.github.io/Advanced_chromatogram_analyzer/](https://anindya-karmaker.github.io/Advanced_chromatogram_analyzer/)
2.  **Or Download:** Download the `index.html` file from this repository and open it in any modern web browser (like Chrome, Firefox, or Edge).

---

### Step-by-Step Workflow

#### 1. Import Your Data
Use **📁 Open ÄKTA File** for Unicorn exports. If the tool detects negative UV values (e.g., baseline drift), a prompt will appear asking if you wish to zero the baseline automatically. Use **⚙️ Custom Import** for other file types.

#### 2. Customize the Plot
Use the **📊 Plot Selection & Styling** panel.
-   Select variables to plot.
-   Customize line styles (solid, dot, dash) and colors.
-   Toggle **Fractions** and **Regions** visibility.
-   Manually set the **X-axis range** for precise views, or double-click the chart to autoscale.

![The main styling panel showing controls for data traces, fractions, and regions.](https://github.com/user-attachments/assets/82dd8dcf-2999-48a9-a941-c845176cfd29)

#### 3. Annotate the Chart
-   **Manage Fractions:** Add, edit, or delete fraction markers.
-   **Label Regions:** Define colored background zones to mark chromatography phases.

<img width="800" height="695" alt="image" src="https://github.com/user-attachments/assets/1c781915-ddab-4fe1-bfc9-fdeb3ec8bee5" />


<img width="798" height="435" alt="image" src="https://github.com/user-attachments/assets/03cbbf2e-6fc5-4243-bbf4-4bb6e6549e24" />

#### 4. Analyze Peaks & Integrate
Go to the **📐 Integration & Analysis** panel:
1.  **Select Variable:** Choose `UV` (or your protein signal).
2.  **Set Range:** Use the `Start` and `End` fields to bracket your peak.
3.  **Baseline Subtraction:** Check **"Use UV-Baseline Corrected Data"** to subtract the baseline signal from the calculation (If present in the UNICORN file).
4.  **Visualize:** Check **"Show Region"** to fill the integrated area with color.
5.  **Results:** View real-time calculations for Area, Volume, Asymmetry, and HETP.

<img width="329" height="481" alt="image" src="https://github.com/user-attachments/assets/71ac620e-bee6-464e-adb8-ecac32dbae88" />

#### 5. Calculate Concentration
Click **🧪 Calculate Concentration**. The tool uses the integrated area (Net Area if baseline correction is active) and your input parameters (Extinction Coefficient, Path Length, MW) to calculate total milligrams.

<img width="798" height="682" alt="image" src="https://github.com/user-attachments/assets/8490113a-0915-4a69-a7d0-6496193f2b79" />


#### 6. Fine-Tune Appearance & Export
-   **Customize Fonts & Layout:** Click **⚙️ Font and Style Settings** to open the advanced editor. Here you can change the chart title, font family, element sizes, label rotation/offsets, and enable **Minor Ticks** for a professional, publication-ready look.
-   **Save or Copy:** Use the `Save as PNG` button to choose a resolution and download the image, or `Copy to Clipboard` to capture the plot for quick use elsewhere.

<img width="595" height="748" alt="image" src="https://github.com/user-attachments/assets/5ae46f00-dc8f-4a43-a41a-3ca3b2909955" />

<img width="595" height="407" alt="image" src="https://github.com/user-attachments/assets/e748063f-0bd4-47f5-9987-5cfad3c0b551" />


## 🛠️ Built With

-   [Plotly.js](https://plotly.com/javascript/) - For interactive charting.
-   [PapaParse](https://www.papaparse.com/) - For robust in-browser CSV parsing.
-   [SheetJS (js-xlsx)](https://sheetjs.com/) - For reading Excel files.
-   Plain HTML, CSS, and JavaScript - No frameworks, no servers, just a single file.

## 📄 License

Developed by Anindya Karmaker. All rights reserved. Unauthorized copy or distribution of this application is strictly prohibited. For inquiries or feedback, please contact the [McDonald-Nandi Lab](https://mcdonald-nandi.ech.ucdavis.edu/).
