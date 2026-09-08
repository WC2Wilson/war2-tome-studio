# Warcraft II TOME Studio

Source editor and resource workbench for Warcraft II `TOME.1` through `TOME.4` archives. It includes the established TOME parser/editor, resource viewers, structured editing tools, archive rebuilding, and validation workflow.

The original workbench validated **870 resources** across the supplied archives and includes decoded/raw extraction, structured text editing, graphics/PUD/GRP inspection, audio catalogs, binary-table tools, archive rebuilding, and round-trip validation.

## Run

Python 3.10+ is enough; no third-party packages are required.

```text
Start_TOME_Studio.bat
```

Or:

```text
python tome_workbench.py
```

## Open archives

Use **File → Open TOME...** to open one or more files, or **Open TOME folder...** to load `TOME.1`, `TOME.2`, `TOME.3`, and `TOME.4` together.

The center list shows each resource's archive index, game resource ID, offset, packed size, detected type, and description. Use the search box to filter the list.

## Extract resources

Select a record, then use the **Resource** menu:

- **Extract selected (decoded)** — writes a usable decoded file when the format is understood;
- **Extract selected raw/packed** — writes the exact record bytes;
- **Extract all decoded** — exports an archive and writes a CSV manifest.

Recognized output types include `.wav`, `.xmi`, `.pud`, `.grp`, `.ppm`, `.pal`, `.tim`, `.iff`, `.txt`, `.dat`, and raw binary data.

## Edit structured strings/dialog data

When the selected record is a recognized string/dialog table, use the structured editor rather than the hex view. Encoded command accelerators are separated into **Hotkey** and **Displayed text**. Applying the edit rebuilds the recognized control sequence and stages the resource in memory.

Click **Save** or **Save As** to write the archive.

## Replace/add/delete resources

The Resource menu supports:

- **Replace selected**;
- **Add resource**;
- **Delete selected**.

Resource length may change. TOME Studio rebuilds the complete offset table when saving. Deleting a record changes IDs after that point, so use deletion only when you understand the game references.

## Graphics

TOME Studio recognizes indexed bitmaps, 256-color palettes, Warcraft II GRP sprite containers, and TIM images. You can browse graphics, change preview palettes, inspect individual GRP frames, zoom, export PPM previews, and batch-export GRP frames.

The GRP parser validates scanline RLE before classifying a resource. In the supplied TOME.1 data the workbench identified 262 GRP resources with 3,250 decodable frames.

## Maps

Complete embedded PUD maps are detected and their chunk structure, dimensions and descriptions are shown. The viewer also provides a diagnostic MTXM minimap. The supplied TOME.1 contained 84 complete PUD resources.

## Audio

The combined audio page catalogs WAVE narration/speech and XMI music across all open archives. WAVE playback uses the Windows audio API; XMI is extracted for use with a compatible player.

## Binary tables / unknown records

Unknown data is never silently rewritten. Use the hex/printable-string view, packing/decode diagnostics, entropy/signature report, or the configurable 8/16/32-bit table viewer. Tables can be exported to CSV for analysis.

## Save and validation

The container format is:

```text
uint32 format_tag
uint16 resource_count
uint16 base_resource_id
uint32 offsets[resource_count]
byte   resources[]
```

On save, TOME Studio rebuilds the offset table, writes the archive, reopens it, and validates the result. Unedited record bytes are preserved.

## Source layout

- `tome_workbench.py` — application, archive parser/writer and viewers/editors;
- `maindat_names.py` — 393 retained symbol references used as research labels only when appropriate;
- `Start_TOME_Studio.bat` — Windows launcher.

No TOME archive or game asset is bundled in this repository. Use files from your own Warcraft II data.
