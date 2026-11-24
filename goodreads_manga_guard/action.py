from calibre.gui2 import warning_dialog
from calibre.gui2.actions import InterfaceAction

from calibre_plugins.goodreads_manga_guard import guard
from calibre_plugins.goodreads_manga_guard.config import PREFS, excluded_tags


class GoodreadsMangaGuardAction(InterfaceAction):
    name = 'Goodreads Manga Guard'
    # No button or menu entry: this plugin only installs the guard.
    action_spec = ('Goodreads Manga Guard', None, 'Keeps manga out of Goodreads progress updates', None)
    dont_add_to = frozenset([
        'toolbar', 'toolbar-device', 'toolbar-child', 'menubar', 'menubar-device',
        'context-menu', 'context-menu-device', 'context-menu-cover-browser', 'context-menu-split'])

    def initialization_complete(self):
        # Every plugin's action exists by now, including Goodreads Sync.
        def notify(msg):
            if PREFS['show_message']:
                self.gui.status_bar.show_message(msg, 8000)

        def log(msg):
            print(msg)

        ok = guard.install(self.gui, excluded_tags, log=log, notify=notify)
        if not ok:
            warning_dialog(
                self.gui, 'Goodreads Manga Guard is not active',
                'Manga are NOT being kept out of Goodreads.\n\nReason: %s.' % guard.STATE.reason,
                show=True)
