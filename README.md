# timew-tagtable

A [Timewarrior](https://timewarrior.net) report extension that prints tracked time as a table: **one row per day, one column per tag**, values in decimal hours. The value block is plain delimiter-separated text, ready to paste into a spreadsheet or timesheet.

```console
$ timew report tagtable :month
2026-09-01 - 2026-09-30 (30 days)
no data: thesis
work	uni	thesis

7.75		
7.00	7.00	
	2.00	
	2.00	
		
		
8.25		
…
```

The lines above the blank line are a header for you to check the range and columns. Everything below it is the data: one line per calendar day, weekends included, with empty cells where nothing was tracked.

## Features

- Fixed, user-defined column order, so the layout stays stable from month to month
- Several tags can be summed into one column
- `*` matches every interval, for a total column
- Every day of the range appears, even days without tracked time
- Configurable delimiter (tab by default)
- Optional copy of the data block to the clipboard (Wayland, `wl-copy`)
- Intervals crossing midnight are split between the two days
- Warns about tags that have no tracked time in the range (catches typos)

## Requirements

- Timewarrior 1.x
- Python ≥ 3.7, standard library only
- Optional: [`wl-clipboard`](https://github.com/bugaevc/wl-clipboard) for copy mode

## Installation

Clone the repository and link the script into Timewarrior's extensions directory:

```sh
git clone https://github.com/butzo/timew-tagtable.git
mkdir -p ~/.config/timewarrior/extensions
ln -s "$PWD/timew-tagtable/tagtable.py" ~/.config/timewarrior/extensions/tagtable.py
```

A symlink lets you update with `git pull`. If you prefer a plain copy:

```sh
install -D -m 755 timew-tagtable/tagtable.py ~/.config/timewarrior/extensions/tagtable.py
```

Older installations use `~/.timewarrior/extensions/` instead of the XDG path.

Verify that Timewarrior finds the extension:

```sh
timew extensions
```

`tagtable.py` should be listed as `Active`. If it isn't, check that the file is executable (`chmod +x`).

## Configuration

Every setting can be defined in `timewarrior.cfg` as a default, or passed on the command line as `rc.<setting>=<value>`. The command line wins.

| Setting              | Default | Required | Description                                                        |
|----------------------|---------|----------|--------------------------------------------------------------------|
| `tagtable.tags`      | –       | yes      | Columns, comma-separated, in order; `+` sums tags, `*` matches all |
| `tagtable.delimiter` | tab     | no       | Column delimiter                                                   |
| `tagtable.copy`      | `no`    | no       | Copy the data block to the clipboard                               |

Example `timewarrior.cfg`:

```ini
tagtable.tags = work,uni+thesis
tagtable.delimiter = tab
tagtable.copy = no
```

### `tagtable.tags`

The comma-separated list of the table's columns. The order of the list is the order of the columns.

Each column is one tag, or several tags joined by `+` whose time is summed: `work,uni+thesis` gives the columns `work` and `uni+thesis`. An interval counts once toward a column if it carries at least one of the column's tags, so an interval tagged both `uni` and `thesis` is not counted twice.

- A column with no tracked time in the range is still shown (empty).
- Every listed tag with no tracked time in the range is named in the header's `no data:` line, including tags inside a `+` group.
- Tags that are tracked but not in the list are ignored.
- The wildcard `*` matches every interval, whatever its tags, including untagged time: `work,uni,*` adds a column with the whole day's tracked time. In a `+` group it makes the group match everything, so `uni+*` is the same column as `*`. It shows up in the `no data:` line only when nothing at all was tracked in the range. Quote it so the shell doesn't expand it to file names: `rc.tagtable.tags='work,*'`.
- To include time without any tag, add the pseudo-tag `untagged`, on its own or in a group: `thesis+untagged`. A real Timewarrior tag named `untagged` can't be told apart from it and is counted together with untagged time, so don't use that name as a tag.
- Quote the value if a tag contains spaces: `rc.tagtable.tags="uni,side project"`.
- Tags containing `+` or `,` cannot be listed, and a tag literally named `*` can't be matched — `*` is always the wildcard.

The report aborts with an error if no tags are configured.

### `tagtable.delimiter`

The string placed between columns, in both the header's tag line and the data rows.

- Any literal string works: `,` `;` `|` …
- Because tabs and spaces are awkward to pass through a shell, three names are also accepted: `tab`, `\t`, `space`.
- An empty value means tab.
- Quote characters that the shell interprets: `rc.tagtable.delimiter=';'`.

Values are numbers or empty, so no CSV-style quoting is applied.

### `tagtable.copy`

When enabled, the data block (everything below the blank line) is sent to the clipboard with `wl-copy`, and the header reports how many rows were copied. The header itself is never copied.

- Enabled by `yes`, `y`, `on`, `true` or `1` (case-insensitive). Anything else disables it.
- If `wl-copy` is missing or fails, the header shows `copy failed: …` and the table is printed as usual.

With copy disabled, select the data block in your terminal manually. The blank line marks where it starts.

### Why `rc.` instead of plain arguments?

Timewarrior treats plain words after the report name as **filter tags** and only passes on intervals that carry *all* of them. `timew report tagtable :month work uni` would therefore drop everything not tagged with both `work` and `uni`. Timewarrior doesn't pass other arguments to extensions, so `rc.` overrides are the only way to hand settings to an extension from the command line.

## Usage

Always pass a range. The table has one row for every day of that range.

```sh
# Current month, settings from timewarrior.cfg
timew report tagtable :month

# Last month, copied to the clipboard
timew report tagtable :lastmonth rc.tagtable.copy=yes

# Explicit range (end is exclusive)
timew report tagtable 2026-09-01 - 2026-10-01

# Different columns for one run
timew report tagtable :month rc.tagtable.tags=uni,thesis

# uni and thesis summed into one column
timew report tagtable :month rc.tagtable.tags=work,uni+thesis

# work, uni, and a total column over all tags
timew report tagtable :month rc.tagtable.tags='work,uni,*'

# Semicolon-separated, e.g. for a spreadsheet import
timew report tagtable :month rc.tagtable.delimiter=';'

# Everything at once
timew report tagtable :lastmonth rc.tagtable.tags=work,uni rc.tagtable.delimiter=tab rc.tagtable.copy=yes
```

Other range hints such as `:week` or `:lastweek` work the same way. Timewarrior also accepts `rc.<setting>:<value>` with a colon instead of `=`.

## Output format

```
<first day> - <last day> (<n> days)        range check
no data: <tag>, …                          only if a tag has no time
<tag>␉<tag>␉…                              column check
copied <n> rows to clipboard               only in copy mode

<value>␉<value>␉…                          one line per day, first day first
…
```

- Values are decimal hours with two decimal places and a point as the decimal separator (`1.75` = 1 h 45 min).
- Days without time for a tag have an empty cell.
- Every data line has the same number of delimiters (tags − 1), so empty cells at the end of a line are kept and columns never shift.
- In copy mode, the clipboard content has no trailing newline.

## How time is counted

- **Timezone:** Timewarrior stores UTC. Days are computed in your system's local timezone, DST included.
- **Midnight:** An interval crossing midnight is split, and each day gets its share.
- **Multiple tags:** An interval counts its full duration once in *each* column it matches. Within a `+` group it counts only once, but an interval that matches several columns counts in all of them, so a row's sum can exceed the time actually tracked. A `*` column is such a case by design: it holds the day's whole tracked time, so it is a total, not another summand.
- **Running interval:** An interval that is still open counts up to now.
- **Range edges:** Intervals are clipped to the report range.

## Limitations

- Copy mode supports Wayland only (`wl-copy`).
- The decimal separator is fixed to a point.
- Tested with simulated Timewarrior report input, not yet against every Timewarrior release.

## License

[AGPL-3.0-or-later](LICENSE). Copyright © 2026 butzo.
