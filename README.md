# Imatest SFRreg Batch Analysis

This project analyzes Imatest SFRreg JSON files and generates:
- Before vs After delta metrics
- Repeatability metrics (mean, std, CV)
- Plots and summary reports

## Requirements
- Python 3.10+

Install dependencies:
```bash
pip install -r requirements.txt
```

## Input Structure
You can run analysis in two ways.

1. Folder-based scan (recommended for standard dataset layout)

Expected root format:
```text
Imatest_data_<EVENT>/
  init/
    [<PREFIX>_]<EVENT>_<SERIAL>_init/
      result/ or Results/
        [<PREFIX>_]<EVENT>_<SERIAL>_<POSITION>_<NN>.json
  after_test/
    [<PREFIX>_]<EVENT>_<SERIAL>_after/
      result/ or Results/
        [<PREFIX>_]<EVENT>_<SERIAL>_<POSITION>_<NN>.json
```

2. Direct path/file input (GUI/Web)
- You can select Before/After folders directly.
- You can also select individual JSON files directly.

## Supported Filename Patterns
The parser now accepts both with and without `VQF12_` prefix.

Supported examples:
- `VQF12_ES2_123_C_01.json`
- `ES2_123_C_01.json`
- `VQF12_ES2_123_C.json` (missing `<NN>` allowed; treated as repeat index `1`)
- `ES2_123_C.json` (missing `<NN>` allowed; treated as repeat index `1`)
- `VQF12_ES2_123_C_tiff.json`
- `ES2_123_C_tiff.json`

## CLI Run
Example:
```bash
python main.py --input Imatest_data_ES2 --output output_ES2
```

## GUI Run
```bash
python gui.py
```
Then select Before/After inputs and output folder, and click **Analyze**.

## Web UI Run
```bash
python web_ui.py
```
Open `http://127.0.0.1:5000` and enter input/output paths.

## Output Files
```text
output_ES2/
  summary_per_json.csv
  summary_per_serial_position.csv
  delta_report.csv
  repeatability_report.csv
  missing_pairs_report.csv (when unmatched keys exist)
  report.md
  chart_guide_ko.md
  figures/
    delta_MTF50.png
    repeatability_MTF50.png
    repeatability_HighBand.png
    MTF_curve_overlay.png
    MTF_curve_overlay_<POSITION>.png
    risk_scatter.png
    before_after_mtf50_by_position.png
    before_after_mtf50_by_position_serial_<SERIAL>.png
    delta_heatmap.png (optional)
```

## Notes
- Missing JSON keys are converted to `NaN` and logged as warnings.
- Files that do not match supported metadata patterns are skipped.
- Pairing key is `(event, serial, position)` between Before and After.
