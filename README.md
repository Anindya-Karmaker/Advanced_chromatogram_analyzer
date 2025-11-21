# Advanced Chromatogram Analyzer

A powerful, browser-based tool for visualizing, analyzing, and exporting chromatography data directly from ÄKTA-generated files or custom CSV/Excel sheets. No installation required.

![Advanced Chromatogram Analyzer Interface](https://github.com/user-attachments/assets/eed13bc4-5cc9-4c74-b3ab-65c0d88bad34)

## 🧬 Overview

This tool was created for researchers who need a fast, private, and flexible way to analyze chromatography data without being tied to proprietary software. It runs entirely in your web browser, meaning your experimental data never leaves your computer. It's designed to be intuitive for daily lab use while providing powerful features for in-depth analysis and generating publication-ready figures.

## 🚀 Key Features

-   **Direct ÄKTA Import:** Natively parses tab-delimited `.txt` or `.csv` files from GE Unicorn software.
-   **Custom Data Import:** A flexible wizard to import data from any generic CSV or Excel (`.xlsx`, `.xls`) file by mapping columns.
-   **Save & Load Sessions:** Save your entire analysis state—including data, annotations, and all settings—into a single `.json` file. Load a session file to resume your work exactly where you left off.
-   **Interactive Multi-Axis Plotting:**
    -   Visualize multiple variables on a single plot, each with its own y-axis.
    -   Full control over line color, thickness, style, and custom labels, with changes reflected instantly.
    -   Zoom and pan capabilities, with a double-click to autoscale and reset the view.
-   **Advanced Peak Analysis:**
    -   Visually select an integration range.
    -   Automatically calculates **Peak Area**, **Volume**, **Asymmetry Factor (As)**, and **HETP**.
    -   Calculations update in real-time as you adjust the integration range.
-   **Rich Annotations & Styling:**
    -   **Fraction Management:** Automatically import, manually add, edit, or remove fractions.
    -   **Fraction Styling:** Customize the color, thickness, and line style (`solid`, `dot`, etc.) of fraction markers directly from the main control panel.
    -   **Label Regions:** Create colored, labeled regions (e.g., "Load", "Wash", "Elution") to clearly annotate different phases of the chromatogram.
-   **Protein Concentration Calculator:** Uses the integrated peak area and Beer-Lambert law parameters to estimate the total protein amount in milligrams.
-   **Publication-Ready Exporting:**
    -   **High-Resolution PNG:** Save the plot as a PNG at **1x, 2x, or 3x resolution**.
    -   **Full Font & Style Customization:** A dedicated modal to control the chart title, font family, sizes, line heights, label rotation, and element offsets.
    -   **Copy to Clipboard:** Instantly copy the plot for pasting into presentations or lab notebooks.
-   **100% Client-Side:** Your data is processed locally in your browser. Nothing is ever uploaded to a server, ensuring complete data privacy.

## ⚙️ How to Use

No installation is needed!

1.  **Visit the Live Tool:** [https://anindya-karmaker.github.io/Advanced_chromatogram_analyzer/](https://anindya-karmaker.github.io/Advanced_chromatogram_analyzer/)
2.  **Or Download:** Download the `index.html` file from this repository and open it in any modern web browser (like Chrome, Firefox, or Edge).

---

### Step-by-Step Workflow

#### 1. Import Your Data
Use the **📁 Open ÄKTA File** button for standard Unicorn exports. For other formats, use **⚙️ Custom Import**. To save your work for later, use **💾 Save Session**, or to resume a previous analysis, use **📂 Load Session**.

#### 2. Customize the Plot
Use the **📊 Plot Selection & Styling** panel. All changes here update the plot instantly.
-   Select variables and customize their **color, line style, thickness, and label**.
-   Toggle visibility and style of **Fractions** and **Regions**.
-   Manually set the **X-axis range** and click **📊 Update Plot** to apply. Double-click the plot to reset the view.

![The main styling panel showing controls for data traces, fractions, and regions.](https://github.com/user-attachments/assets/82dd8dcf-2999-48a9-a941-c845176cfd29)


#### 3. Annotate the Chart
-   **Manage Fractions:** Use the **🧫 Fractions** panel to add, edit, or hide fraction markers.
-   **Label Regions:** Use the **🎨 Label Regions** panel to define and color important sections like "Wash" or "Elution". These appear as shaded areas and are listed in the legend.

#### 4. Analyze Peaks
-   **Enter Column Parameters:** Input your column's length in millimeters for accurate HETP calculation.
-   **Integrate a Peak:** In the **📐 Integration & Analysis** panel, select your primary variable (usually `UV`) and use the `Start` and `End` fields to define the peak boundaries. The `Area`, `Volume`, `Asymmetry`, and `HETP` are calculated automatically.

![The integration panel showing real-time calculations for peak analysis.](https://github.com/user-attachments/assets/171a8ef9-7245-4f61-bd58-a36cd8294d2f)

#### 5. Calculate Concentration
The **Amount (mg)** is calculated automatically in the integration panel. To adjust parameters, click **🧪 Calculate Concentration**, enter your protein's specific values (Ext. Coeff., Path Length, MW), and the amount will update in real-time.

![The concentration calculator modal for applying Beer-Lambert law parameters.](https://github.com/user-attachments/assets/02a4d8ca-4b03-4610-a774-2b26bc914fc9)

#### 6. Fine-Tune Appearance & Export
-   **Customize Fonts & Layout:** Click **⚙️ Font and Style Settings** to open the advanced editor. Here you can change the chart title, font family, element sizes, label rotation/offsets, and fraction line height to achieve a professional, publication-ready look.
-   **Save or Copy:** Use the `Save as PNG` button to choose a resolution and download the image, or `Copy to Clipboard` to capture the plot for quick use elsewhere.

![The font and style settings modal, providing deep customization for exporting.](https://github.com/user-attachments/assets/6f7e3500-b7a6-4489-959a-523fbc5b14b5)

## 🛠️ Built With

-   [Plotly.js](https://plotly.com/javascript/) - For interactive charting.
-   [PapaParse](https://www.papaparse.com/) - For robust in-browser CSV parsing.
-   [SheetJS (js-xlsx)](https://sheetjs.com/) - For reading Excel files.
-   Plain HTML, CSS, and JavaScript - No frameworks, no servers, just a single file.

## 📄 License

All rights reserved. Unauthorized copy or distribution of this application is strictly prohibited. For inquiries, please contact the [McDonald-Nandi Lab](https://mcdonnanld-nandi.ech.ucdavis.edu/).
