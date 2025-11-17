Advanced Chromatogram Analyzer
A powerful, browser-based tool for visualizing, analyzing, and exporting chromatography data directly from ÄKTA-generated files or custom CSV/Excel sheets. No installation required.
![alt text](https://github.com/user-attachments/assets/f734d6d6-b47c-499f-b877-4f28f520cff2)
🧬 Overview
This tool was created for researchers who need a fast, private, and flexible way to analyze chromatography data without being tied to proprietary software. It runs entirely in your web browser, meaning your experimental data never leaves your computer. It's designed to be intuitive for daily lab use while providing powerful features for in-depth analysis and generating publication-ready figures.
🚀 Key Features
Direct ÄKTA Import: Natively parses tab-delimited .txt or .csv files exported from GE Unicorn software (tested with v7.xx).
Custom Data Import: A flexible wizard to import data from any generic CSV or Excel (.xlsx, .xls) file by mapping columns.
Interactive Multi-Axis Plotting:
Visualize up to 6 different variables on a single plot, each with its own y-axis.
Full control over line color, line style (solid, dash, dot), and custom labels for each trace.
Peak Integration & Analysis:
Visually select an integration range using sliders.
Automatically calculates peak area (in mL·mAU) and volume.
Protein Concentration Calculator: Uses the integrated peak area and Beer-Lambert law parameters to estimate the total protein amount in milligrams.
Fraction Management:
Automatically imports fraction data from ÄKTA files.
Manually add, edit, or remove fractions.
Toggle fraction visibility on the plot, with labels displayed as annotations.
Exporting Options:
Save as PNG: Export the customized plot as a high-resolution image.
Copy to Clipboard: Instantly copy the plot for pasting into presentations or lab notebooks.
Export Data (CSV): Export the processed data for use in other software like Prism or Excel.
100% Client-Side: Your data is processed locally in your browser. Nothing is ever uploaded to a server, ensuring complete data privacy.
⚙️ How to Use
No installation is needed!
Download: Download the chrom_analyzer_web.html file from this repository.
Open: Open the file in any modern web browser (like Chrome, Firefox, or Edge).
Step-by-Step Workflow
1. Import Your Data
Use the 📁 Open ÄKTA File button for standard Unicorn exports.
Use the ⚙️ Custom Import button for any other CSV or Excel file. A preview will appear, allowing you to map your data columns (e.g., which column is volume, which is UV, etc.).
2. Customize the Plot
The 📊 Plot Selection & Styling panel gives you full control over the graph's appearance.
Select variables to display using the checkboxes.
Change the label that appears in the legend and on the axis.
Pick a color for each line.
Choose a line style (solid, dash, dot, etc.).
Click 📊 Update Plot to apply your changes.
![alt text](https://github.com/user-attachments/assets/753c8e5c-9747-48e7-b373-7447c09fb753)
3. Analyze Peaks
In the 📐 Integration & Analysis panel, select your primary variable for integration (usually UV).
Use the Start and End input fields to define the boundaries of your peak.
The Area, Volume, and Range are calculated and displayed automatically.
4. Calculate Concentration
After integrating a peak, click the 🧪 Calculate Concentration button.
A modal will appear with your integration results.
Enter your protein's Molar Extinction Coefficient, the flow cell Path Length (defaults to 0.2 cm for a standard 2 mm cell), and the Molecular Weight.
The final amount in milligrams is calculated in real-time.
![alt text](https://github.com/user-attachments/assets/6d7e6402-3691-4c52-9440-d29e9f49dca7)
5. Export Your Results
Use the buttons in the 💾 Export & Actions panel to save your work.
🛠️ Built With
Plotly.js - For interactive charting.
PapaParse - For robust in-browser CSV parsing.
SheetJS (js-xlsx) - For reading Excel files.
Plain HTML, CSS, and JavaScript - No frameworks, no servers, just a single file.
📄 License
All rights reserved. Unauthorized copy or distribution of this application is strictly prohibited. For inquiries, please contact the repository owner.
