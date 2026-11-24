import functools
import sys
import types
import unittest
from pathlib import Path

pkg = types.ModuleType('gmg_test')
pkg.__path__ = [str(Path(__file__).resolve().parents[1] / 'goodreads_manga_guard')]
sys.modules[pkg.__name__] = pkg
from gmg_test import guard  # noqa: E402

TAGS = {1: ['Fiction', 'Fantasy'], 2: ['Manga'], 3: ['manga', 'Comics'], 4: [], 5: ['Mystery']}


class FakeApi(object):
    def __init__(self, tags, fail=False):
        self.tags, self.fail = tags, fail

    def field_for(self, name, bid):
        if self.fail:
            raise RuntimeError('db unavailable')
        assert name == 'tags'
        return self.tags.get(bid)


class FakeView(object):
    def __init__(self, selected, fail_select=False):
        self.selected, self.fail_select, self.reselected = list(selected), fail_select, []

    def get_selected_ids(self):
        return list(self.selected)

    def select_rows(self, ids):
        if self.fail_select:
            raise RuntimeError('cannot select')
        self.reselected.append(list(ids))
        self.selected = list(ids)


class FakeGoodreads(object):
    def __init__(self, view):
        self.view, self.calls = view, []

    def update_reading_progress(self, action, user_name):
        self.calls.append((action, user_name, list(self.view.selected)))
        return 'dialog'


class FakeGui(object):
    def __init__(self, selected, tags=TAGS, with_goodreads=True, **kw):
        self.library_view = FakeView(selected, kw.get('fail_select', False))
        self.current_db = types.SimpleNamespace(new_api=FakeApi(tags, kw.get('fail_tags', False)))
        self.iactions = {}
        self.goodreads = FakeGoodreads(self.library_view)
        if with_goodreads:
            self.iactions[guard.GOODREADS_ACTION] = self.goodreads


class Harness(object):
    def __init__(self, selected, excluded=('Manga',), **kw):
        self.gui = FakeGui(selected, **kw)
        self.state = guard.GuardState()
        self.messages, self.logs = [], []
        self.ok = guard.install(self.gui, lambda: list(excluded), self.state,
                                log=self.logs.append, notify=self.messages.append)

    def call(self):
        return self.gui.iactions[guard.GOODREADS_ACTION].update_reading_progress('progress', 'Ebran')


class SplitTests(unittest.TestCase):
    def test_split(self):
        kept, dropped = guard.split_selection([1, 2, 3, 4], TAGS.get, ['manga'])
        self.assertEqual((kept, dropped), ([1, 4], [2, 3]))      # case-insensitive

    def test_several_tags_and_blank_entries(self):
        kept, dropped = guard.split_selection([1, 2, 5], TAGS.get, ['Mystery', ' ', '', 'Manga'])
        self.assertEqual((kept, dropped), ([1], [2, 5]))

    def test_no_excluded_tags_drops_nothing(self):
        self.assertEqual(guard.split_selection([1, 2], TAGS.get, []), ([1, 2], []))

    def test_book_without_tags(self):
        self.assertEqual(guard.split_selection([4], TAGS.get, ['Manga']), ([4], []))
        self.assertEqual(guard.split_selection([99], TAGS.get, ['Manga']), ([99], []))

    def test_parse_tags(self):
        self.assertEqual(guard.parse_tags(' Manga, Comics ,,'), ['Manga', 'Comics'])
        self.assertEqual(guard.parse_tags(None), [])


class InstallTests(unittest.TestCase):
    def test_manga_are_dropped_and_novels_go_through(self):
        h = Harness([1, 2, 4, 3])
        self.assertTrue(h.ok)
        self.assertEqual(h.call(), 'dialog')
        action, user, selection = h.gui.goodreads.calls[0]
        self.assertEqual((action, user), ('progress', 'Ebran'))
        self.assertEqual(selection, [1, 4])
        self.assertEqual(h.gui.library_view.selected, [1, 4])
        self.assertTrue(any('skipped 2 manga' in m for m in h.messages))
        self.assertEqual((h.state.last_skipped, h.state.skipped_total), (2, 2))

    def test_all_manga_means_no_dialog_at_all(self):
        h = Harness([2, 3])
        self.assertIsNone(h.call())
        self.assertEqual(h.gui.goodreads.calls, [])
        self.assertTrue(any('nothing else to update' in m for m in h.messages))

    def test_no_manga_is_untouched(self):
        h = Harness([1, 4, 5])
        self.assertEqual(h.call(), 'dialog')
        self.assertEqual(h.gui.goodreads.calls[0][2], [1, 4, 5])
        self.assertEqual(h.gui.library_view.reselected, [])          # selection never rewritten
        self.assertEqual(h.messages, [])

    def test_arguments_and_result_are_forwarded(self):
        h = Harness([1])
        self.assertEqual(h.gui.iactions[guard.GOODREADS_ACTION].update_reading_progress('progress', 'X'), 'dialog')
        self.assertEqual(h.gui.goodreads.calls[0][:2], ('progress', 'X'))

    def test_extra_arguments_in_a_future_version_still_work(self):
        h = Harness([1])
        gr = h.gui.goodreads
        gr.update_reading_progress = lambda *a, **k: ('called', a, k)   # simulate a changed signature
        guard.uninstall(h.gui, h.state)
        guard.install(h.gui, lambda: ['Manga'], h.state)
        self.assertEqual(gr.update_reading_progress('progress', 'U', 'extra', flag=True),
                         ('called', ('progress', 'U', 'extra'), {'flag': True}))

    def test_installing_twice_does_not_stack(self):
        h = Harness([2, 1])
        self.assertTrue(guard.install(h.gui, lambda: ['Manga'], h.state))
        h.call()
        self.assertEqual(len(h.gui.goodreads.calls), 1)
        self.assertEqual(h.state.skipped_total, 1)                    # counted once, not twice

    def test_missing_goodreads_plugin(self):
        h = Harness([1], with_goodreads=False)
        self.assertFalse(h.ok)
        self.assertFalse(h.state.installed)
        self.assertIn('not found', h.state.reason)

    def test_changed_goodreads_plugin(self):
        gui = FakeGui([1])
        gui.iactions[guard.GOODREADS_ACTION] = object()               # no update_reading_progress
        state = guard.GuardState()
        self.assertFalse(guard.install(gui, lambda: ['Manga'], state))
        self.assertIn('update_reading_progress', state.reason)

    def test_uninstall_restores_the_original(self):
        h = Harness([2, 1])
        guard.uninstall(h.gui, h.state)
        self.assertFalse(h.state.installed)
        h.gui.library_view.selected = [2, 1]
        h.call()
        self.assertEqual(h.gui.goodreads.calls[0][2], [2, 1])        # unfiltered again

    def test_menu_entries_built_before_install_are_not_guarded(self):
        # The Goodreads menu binds the method with functools.partial when it builds the menu,
        # so a manual choice from that menu is untouched; only calls looked up later (Kobo Utilities) are.
        gui = FakeGui([2, 1])
        menu_entry = functools.partial(gui.goodreads.update_reading_progress, 'progress', 'U')
        guard.install(gui, lambda: ['Manga'], guard.GuardState())
        menu_entry()
        self.assertEqual(gui.goodreads.calls[0][2], [2, 1])
        gui.library_view.selected = [2, 1]
        gui.iactions[guard.GOODREADS_ACTION].update_reading_progress('progress', 'U')
        self.assertEqual(gui.goodreads.calls[1][2], [1])


class FailClosedTests(unittest.TestCase):
    """If the guard cannot be sure manga are out, nothing goes to Goodreads."""

    def test_cannot_read_tags(self):
        h = Harness([1, 2], fail_tags=True)
        self.assertIsNone(h.call())
        self.assertEqual(h.gui.goodreads.calls, [])
        self.assertIn('could not check', h.state.last_problem)
        self.assertTrue(h.messages)

    def test_cannot_change_selection(self):
        h = Harness([1, 2], fail_select=True)
        self.assertIsNone(h.call())
        self.assertEqual(h.gui.goodreads.calls, [])
        self.assertIn('could not change', h.state.last_problem)

    def test_all_manga_never_needs_the_selection_to_change(self):
        h = Harness([2, 3], fail_select=True)
        self.assertIsNone(h.call())
        self.assertEqual(h.state.last_problem, '')


if __name__ == '__main__':
    unittest.main()
