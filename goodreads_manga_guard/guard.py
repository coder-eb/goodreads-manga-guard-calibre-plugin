"""Keep manga out of Goodreads Sync's "Update reading progress" dialog.

Kobo Utilities, after storing reading positions, selects every changed book and calls
``gui.iactions['Goodreads Sync'].update_reading_progress(action, user)``. That dialog
pushes every book it can link - and it links books by ISBN on its own - so manga end
up on Goodreads. This module replaces that one method, on the running object only,
with a wrapper that first drops the excluded books (by tag) from the selection.

Nothing on disk is changed, and the change disappears when Calibre closes. If
Goodreads Sync is missing or has changed, the guard does not install and says so.

Pure Python (the Calibre objects are duck-typed), so it is unit tested without Calibre.
"""

import time

GOODREADS_ACTION = 'Goodreads Sync'      # the key Kobo Utilities looks it up by
METHOD = 'update_reading_progress'


class GuardState(object):
    def __init__(self):
        self.installed = False
        self.reason = 'not started'
        self.skipped_total = 0
        self.last_skipped = 0
        self.last_time = None
        self.last_problem = ''


STATE = GuardState()


def split_selection(book_ids, tags_of, excluded_tags):
    """``(kept, dropped)``: dropped = books carrying any excluded tag (case-insensitive)."""
    excluded = {t.strip().casefold() for t in excluded_tags if t and t.strip()}
    kept, dropped = [], []
    for bid in book_ids:
        tags = {t.casefold() for t in (tags_of(bid) or ())}
        (dropped if tags & excluded else kept).append(bid)
    return kept, dropped


def parse_tags(text):
    return [t.strip() for t in (text or '').split(',') if t.strip()]


def install(gui, get_excluded_tags, state=STATE, log=lambda m: None, notify=lambda m: None):
    """Wrap Goodreads Sync's progress update. Returns True when the guard is active."""
    iaction = getattr(gui, 'iactions', {}).get(GOODREADS_ACTION)
    if iaction is None:
        state.installed, state.reason = False, 'the Goodreads Sync plugin was not found'
        return False
    original = getattr(iaction, METHOD, None)
    if not callable(original):
        state.installed = False
        state.reason = "Goodreads Sync has no '%s' method (the plugin changed)" % METHOD
        return False
    if getattr(original, '_manga_guard', False):
        state.installed, state.reason = True, 'active'
        return True

    def guarded(*args, **kwargs):
        try:
            selected = list(gui.library_view.get_selected_ids())
            api = gui.current_db.new_api
            kept, dropped = split_selection(
                selected, lambda b: api.field_for('tags', b), get_excluded_tags())
        except Exception as exc:                      # cannot tell what is manga: do nothing
            state.last_problem = 'could not check the selection: %s' % exc
            log('[Goodreads Manga Guard] ' + state.last_problem)
            notify('Goodreads Manga Guard could not check the selection, so Goodreads was '
                   'not updated. Use the Goodreads menu for novels.')
            return None
        if not dropped:
            return original(*args, **kwargs)
        state.skipped_total += len(dropped)
        state.last_skipped, state.last_time = len(dropped), time.time()
        if not kept:
            notify('Goodreads Manga Guard: skipped %d manga; nothing else to update.' % len(dropped))
            return None
        try:
            gui.library_view.select_rows(kept)
        except Exception as exc:                      # cannot enforce the filter: do nothing
            state.last_problem = 'could not change the selection: %s' % exc
            log('[Goodreads Manga Guard] ' + state.last_problem)
            notify('Goodreads Manga Guard could not remove manga from the selection, so '
                   'Goodreads was not updated.')
            return None
        notify('Goodreads Manga Guard: skipped %d manga.' % len(dropped))
        return original(*args, **kwargs)

    guarded._manga_guard = True
    guarded.__wrapped__ = original
    setattr(iaction, METHOD, guarded)
    state.installed, state.reason = True, 'active'
    return True


def uninstall(gui, state=STATE):
    """Remove the wrapper (restores Goodreads Sync's own method)."""
    iaction = getattr(gui, 'iactions', {}).get(GOODREADS_ACTION)
    if iaction is not None and getattr(getattr(iaction, METHOD, None), '_manga_guard', False):
        try:
            delattr(iaction, METHOD)          # drops the instance attribute; the class method shows again
        except AttributeError:
            pass
    state.installed, state.reason = False, 'removed'
