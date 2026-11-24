# Goodreads Manga Guard (Calibre plugin)

Keeps books tagged **Manga** out of the **Goodreads Sync** plugin's "Update reading progress" dialog,
including the automatic update that **Kobo Utilities** triggers after it stores reading positions.

## Why

After Kobo Utilities stores your reading positions it selects every changed book and calls Goodreads
Sync's progress update. That dialog pushes every book it can link, and it links books by **ISBN on its
own**, writing the Goodreads id back to Calibre. So manga with an ISBN end up on Goodreads even if you
never linked them.

## What it does

Adds no button or menu entry. When Calibre starts it replaces **one method** on the running
Goodreads Sync object (`update_reading_progress`) with a wrapper that first drops excluded books
(by tag, default `Manga`, case-insensitive) from the library selection, then calls the original.

- Only manga changed: no Goodreads dialog; the status bar says "skipped N manga".
- Novels and manga changed: the dialog lists only the novels.
- Nothing on disk is modified (not Goodreads Sync, not Kobo Utilities, not your library). The change
  lives in memory and disappears when Calibre closes or the plugin is removed.
- **Fails closed:** if it cannot read the tags or change the selection, it sends nothing to Goodreads and
  says so, rather than risk sending manga.
- **Fails visibly:** if Goodreads Sync is missing or has changed (no `update_reading_progress`), the guard
  does not install and shows a warning at startup. The settings page shows ACTIVE / NOT ACTIVE.

The Goodreads menu's own "Update reading progress" entry is built before the guard installs, so choosing
it by hand is not filtered.

## Depends on

- the plugin name `Goodreads Sync` (the key Kobo Utilities looks it up by),
- the method `update_reading_progress(action, user_name)`,
- Calibre's `library_view.get_selected_ids()` / `select_rows()` and `db.new_api.field_for('tags', id)`.

Checked against Goodreads Sync 1.17.4 and Kobo Utilities 2.29.0. If an update renames the method the guard
turns itself off and tells you; if Kobo Utilities stopped calling it, the guard would simply never trigger
(manga would reappear in the Goodreads dialog).

## Install

```
make zip
calibre-customize -a goodreads_manga_guard-v0.1.0.zip
```

Restart Calibre, then open Preferences > Plugins > Goodreads Manga Guard > Customize plugin; it should say
**ACTIVE**. Tags to exclude are set there (comma separated).

## Tests

`python -m pytest tests` (18 unit tests with fake Calibre objects: manga dropped, novels untouched,
all-manga selections, fail-closed cases, missing/changed Goodreads plugin, installing twice).
Also loaded in a throwaway Calibre config next to the real Goodreads Sync plugin to confirm the real class
name and method signature match. Not tested against a real Kobo sync.
