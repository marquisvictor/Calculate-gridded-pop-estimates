# GRID3 Population CLI

Estimate population for Nigerian wards, local government areas (LGAs), or a custom city polygon using GRID3 population rasters. **No QGIS or ArcGIS installation is needed.**

This tool extends Victor Irekponor's Lagos Island BSc dissertation workflow into a reproducible command line application. It downloads data, selects polygons, calculates fractional zonal population sums, checks the result, and exports tables and optional maps.

**Use 64-bit Python 3.12 for the documented installation.** Windows has been tested locally. GitHub Actions is configured to test Windows, macOS, and Linux; check the Actions tab for its actual status. The Mac instructions cover Apple Silicon and Intel MacBooks. Create a separate Python environment on each computer; a Windows environment cannot be copied to a Mac.

## What population are we estimating?

The built-in downloader uses Nigeria population **v3.0, representing 2025**, and GRID3 operational wards **v3.0, released in 2026**. Ward v3 coverage includes Ogun but currently covers only 24 states. The estimate command accepts other appropriate boundary datasets for the remaining states.

The output means **estimated 2025 population within the selected boundaries**. A later download date does not change the population reference year. An LGA polygon is dissolved from that LGA's supplied wards, so its definition follows those wards. Combined Abeokuta North/South results describe that administrative study area. A city-footprint estimate requires a separately defined urban polygon.

The repository contains source code, tests, and instructions. Downloaded rasters, environments, generated results, and personal dissertation files are excluded. Each computer downloads its own inputs. GRID3 data downloads do not need an API key.

## Windows: installation and first run

Use **PowerShell** for these commands. Run the steps in order.

### 1. Install Python and Git

Install 64-bit Python 3.12 from [Python's Windows downloads](https://www.python.org/downloads/windows/), including the Python launcher. Install [Git for Windows](https://git-scm.com/download/win). Close and reopen PowerShell after installation.

```powershell
py -3.12 --version
git --version
```

Python should report `3.12.x`. If `py` is unavailable but `python --version` shows 3.12, replace `py -3.12` below with `python`.

### 2. Clone the code

```powershell
git clone https://github.com/marquisvictor/grid3-population-cli.git
cd grid3-population-cli
```

If the repository is private, authenticate with a GitHub account that has access. Git's browser sign-in or `gh auth login` can authenticate HTTPS Git. Your normal GitHub password is not an HTTPS Git password. See [GitHub authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

### 3. Create an environment and install dependencies

Run these from the cloned folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands use the environment's Python directly. Activation is optional; this avoids PowerShell activation-script restrictions. Supported binary packages include the geospatial libraries, so separate QGIS/GDAL installation is unnecessary when the wheels install successfully.

### 4. Analyse Abeokuta South wards

```powershell
.\.venv\Scripts\python.exe run.py --lga "Abeokuta South" --level ward --plot
```

The first run downloads the national population raster and Ogun boundaries into `data/`. Later runs reuse them. The tool prints the population total and results folder. Installation/downloads need internet; estimation can run offline once inputs exist.

### 5. Optional Windows shortcut

```powershell
.\run.ps1 -Lga 'Abeokuta South' -Level ward -Plot
.\run.ps1 -Lga 'Abeokuta North','Abeokuta South' -Level lga
```

If PowerShell blocks this script, use the direct Python command above. No system execution-policy change is required. The shortcut needs `.venv` in the repository.

## MacBook: installation and first run

Use the **Terminal** application, on either Apple Silicon (M-series) or Intel Macs.

### 1. Install Python and Git

Install a Python 3.12 **universal2** build from [Python's macOS downloads](https://www.python.org/downloads/macos/). Universal2 supports both Intel and Apple Silicon. Prefer native ARM Python on Apple Silicon and keep Python/package architectures consistent. See [Python's Mac guidance](https://docs.python.org/3.12/using/mac.html).

```bash
python3.12 --version
git --version
```

If `git --version` prompts you to install Apple's Command Line Tools, complete the installation and retry. If only `python3` is available and its version is 3.12, substitute it for `python3.12` below.

### 2. Clone the code

```bash
git clone https://github.com/marquisvictor/grid3-population-cli.git
cd grid3-population-cli
```

For a private repository, use an account with access. One option is [GitHub CLI](https://cli.github.com/): install it, run `gh auth login`, choose GitHub.com and HTTPS, complete browser authentication, and agree to authenticate Git. Then clone. Do not put a token in a clone URL.

### 3. Create the environment and install dependencies

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### 4. Analyse Abeokuta South wards

```bash
.venv/bin/python run.py --lga "Abeokuta South" --level ward --plot
```

This downloads inputs on the first run and prints a results folder. No Windows emulator or GIS application is needed. Use the Python runner on a Mac; `run.ps1` is a Windows convenience script.

## More examples

Below, `python` means your environment's Python. Either replace it with `.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Mac, or activate the environment first:

```powershell
# Windows PowerShell (optional)
.\.venv\Scripts\Activate.ps1
```

```bash
# Mac Terminal (optional)
source .venv/bin/activate
```

If Windows activation is blocked, use the direct Python path; activation is not necessary.

### Wards across both Abeokuta LGAs

```bash
python run.py --state Ogun --lga "Abeokuta North" --lga "Abeokuta South" --level ward --plot
```

Repeat `--lga` for multiple areas. With no arguments, `python run.py` defaults to both Abeokuta LGAs and ward totals.

### One total per LGA

```bash
python run.py --lga "Abeokuta North" --lga "Abeokuta South" --level lga
```

### One ward

```bash
python run.py --lga "Abeokuta South" --ward "Ake 1" --level ward
```

Repeat `--ward` for multiple wards. Include the LGA to disambiguate recurring ward names. Name matching ignores case and surrounding whitespace; otherwise names must match the dataset exactly.

### Another Ogun LGA

```bash
python run.py --state Ogun --lga "Ijebu Ode" --level ward
```

For another supported state, change `--state` and supply its LGA name. The runner requires an explicit LGA outside Ogun. For a whole state, use the lower-level command below without `--lga`.

### One combined administrative study area

```bash
python run.py --lga "Abeokuta North" --lga "Abeokuta South" --level area --name "Abeokuta North and South"
```

### A chosen city footprint

Supply a valid polygon file that explicitly defines the urban area:

```bash
python estimate_population.py estimate --raster data/NGA_population_v3_0_gridded.tif --boundaries abeokuta_city.geojson --level area --name "Abeokuta urban footprint" --year 2025 --population-version 3.0 --boundary-version "user-defined city boundary" --out results/abeokuta_city
```

The tool sums within your polygon; it does not automatically identify where the city ends. Document how you chose this boundary.

### Choose where to save results

```bash
python run.py --lga "Abeokuta South" --out results/south_run_01
```

Use a new folder. Nonempty output folders are rejected to preserve earlier results. If `--out` is omitted, `run.py` creates a timestamped folder.

## Download and inspect inputs

```bash
python estimate_population.py download --state Ogun --out data
python estimate_population.py inspect --boundaries data/ogun_wards_v3.geojson --raster data/NGA_population_v3_0_gridded.tif
```

The download command retrieves the population archive, extracts the actual population GeoTIFF, downloads its release statement, and retrieves all state wards in batches to avoid server record limits. Files include:

- `data/NGA_population_v3_0_gridded.tif`: people per cell.
- `data/ogun_wards_v3.geojson`: operational ward boundaries.
- `data/NGA_population_v3_0_README.pdf`: population release statement.
- `data/sources.json`: URLs, versions, retrieval time, feature count, and hashes.

An explicit `download` reuses completed population archives and refreshes the state's polygons. Preserve identical input files when exact reproduction matters. The convenience runner downloads only if required inputs are absent.

The downloader is pinned to wards v3.0 (24 states). For other states, supply appropriate boundaries separately (for example a suitable v1 release). Do not combine overlapping releases without choosing the intended coverage.

```bash
python run.py --help
python estimate_population.py --help
python estimate_population.py estimate --help
```

## Use custom or legacy datasets

Boundary formats include GeoJSON, shapefile, and GeoPackage. Keep shapefile companion files together, including `.dbf`, `.shx`, `.prj`, and encoding information. Use `--layer` for a GeoPackage with multiple layers.

The raster must be single-band, unrotated, **people per cell**, with a known CRS. A settlement mask or people-per-square-kilometre density raster cannot be substituted directly.

Both new (`state`, `lga`, `ward`) and old dissertation (`state_name`, `lga_name`, `ward_name`) fields are automatically recognized. Other names can be supplied:

```bash
python estimate_population.py estimate --raster population.tif --boundaries wards.gpkg --layer wards --state-field STATE --lga-field LGA --ward-field WARD --state Ogun --lga "Abeokuta South" --level ward --year 2025 --boundary-version "my boundary release" --out results/custom_run
```

Omit `--lga` to process a whole state. `--level ward` groups by state/LGA/ward name; `--level lga` dissolves by state/LGA; `--level area` unions all selected polygons into one result. Independently supplied LGA polygons can use `--level lga` with their LGA field. For arbitrary individual zones, provide a unique zone-name field through `--ward-field` and use `--level ward`; the label does not change the mathematics.

## Output files

| File | Contents |
|---|---|
| `population.csv` | Names, estimated population, valid cell equivalents |
| `population.geojson` | Output polygons in WGS84 and their results |
| `run.json` | Command, input paths/hashes, declared year/versions, method, raster metadata, totals/checks |
| `population_map.png` | Optional map of total population per zone |

Open the CSV in Excel, Numbers, R, or Python. `valid_cell_equivalents` is the sum of covered fractions of valid cells, **not people**; it can be fractional. The map shows total population, not density. Small wards may be hard to see at full-LGA scale.

Keep decimals during calculations and round only displayed totals. `run.json` records absolute paths on the computer that ran it; review those paths before sharing metadata.

## Calculation and limits

```text
zone population = sum(cell population × fraction of cell inside zone)
```

`exactextract` calculates fractional coverage. A cell with 100 people and 25% inside a ward contributes 25 people. This assumes uniform population within partly intersected cells; it cannot place individuals more precisely than the input grid.

Polygons are transformed into the raster CRS. The raster is not resampled or converted to vectors. Coverage fractions are calculated in raster coordinates. Values already represent people per cell, so no extra multiplication by cell area is performed.

Checks reject empty selections, unknown names, missing CRS, invalid polygons, significant overlapping output zones, polygons outside the raster, invalid aggregate values, and zones containing no valid cells. Zone sums must agree with an independent extraction over their union. Overlaps are measured in an equal-area CRS.

Gaps cannot be detected without an independent reference polygon. Rows sharing state/LGA/ward names are dissolved; uniquely identify different wards with identical names. A dissolve/union intentionally merges input pieces; overlap checks apply to final output zones.

NoData is excluded. In this v3 raster, NA means mapped unsettled areas within Nigeria or areas outside the national boundary. All-NoData zones are rejected for investigation; a valid numerical zero is different. Consult the specific release statement for other rasters.

These are modelled estimates, not official census figures. Summing cell means does not provide a valid uncertainty interval. This tool does not train a new population model, estimate commuters, project growth, or calculate service demand.

## Pull updates on another computer

Inside the cloned folder:

```bash
git pull --ff-only
python -m pip install -r requirements.txt
```

Use the environment's direct Python path if it is not activated. Pulling updates the code and README; it does not transfer another computer's data or results. Download the inputs locally and copy custom boundaries separately. Commit or set aside local source edits before pulling; do not force an update over work you want to keep.

## Troubleshooting

| Problem | What to do |
|---|---|
| Python command not found | Install Python 3.12, reopen the terminal, and verify the executable name. |
| Git command not found | Install Git; on Mac complete Apple's Command Line Tools prompt. |
| Clone says repository not found | Check the URL and account access if private. |
| Missing Python module | Install requirements with the same `.venv` Python used to run the tool. |
| PowerShell blocks scripts | Use `.\.venv\Scripts\python.exe run.py ...` directly. |
| pip tries to compile geospatial packages | Use supported 64-bit Python 3.12 and upgrade pip; match the Mac's CPU architecture. |
| Mac SSL certificate verification fails | For Python.org's installer, run `Install Certificates.command` in the Python folder under Applications. Do not disable TLS verification. |
| Download times out | Check internet and retry. Incomplete `.part` files are redownloaded. |
| No v3 wards for state | Supply another boundary dataset to the estimate command. |
| Unknown name | Run `inspect` and copy the exact LGA/ward name. |
| Boundary outside raster | Use the national/full-coverage raster rather than a clipped one. |
| Invalid geometry/all-NoData | Inspect and correct the source before reporting totals. |
| Output folder exists | Choose a new folder or omit `--out` in `run.py`. |

Newer Python releases may need different binary package builds; use 3.12 for this documented installation.

## Sources and attribution

- [Nigeria population downloads](https://data.worldpop.org/repo/wopr/NGA/population/v3.0/).
- [Population release statement](https://data.worldpop.org/repo/wopr/NGA/population/v3.0/NGA_population_v3_0_README.pdf).
- [Operational wards v3.0](https://www.arcgis.com/home/item.html?id=45cd2ef592094d12aca43113a90a6054).
- [GRID3 Nigeria catalogue](https://grid3.org/geospatial-data-nigeria).
- [exactextract](https://github.com/isciences/exactextract).
- [Python on Windows](https://docs.python.org/3.12/using/windows.html) and [Python on Mac](https://docs.python.org/3.12/using/mac.html).

Cite Nnanatu C.C., Gadiaga A., Abbott T. J., Chamberlain H., Lazar A. N., and Tatem A. J. (2025), *Modelled gridded population estimates for Nigeria 2025 version 3.0*, WorldPop, University of Southampton, [DOI 10.5258/SOTON/WP00782](https://doi.org/10.5258/SOTON/WP00782). Cite GRID3/CIESIN wards according to their metadata. Consult the datasets' CC BY 4.0 attribution terms before redistributing data or derived results; their licensing is separate from source code.
