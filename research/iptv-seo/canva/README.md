# Data files for the text list

Designed HTML boards are not used. The list to read is:

```text
research/iptv-seo/LIST.txt
```

Same content is copied to `research/iptv-seo/AVAILABLE_LIST.txt`.

Rebuild:

```text
python3 research/iptv-seo/rebuild_lists.py
python3 research/iptv-seo/generate_text_list.py
```

`traffic.json` holds verified Semrush keyword volumes only (never invented).
`iptv-domains-canva-import.csv` is a machine table of the same available/confirm names if you still want to paste into a spreadsheet.
