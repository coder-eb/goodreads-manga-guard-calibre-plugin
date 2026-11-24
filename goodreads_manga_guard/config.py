from calibre.utils.config import JSONConfig
from qt.core import QCheckBox, QFormLayout, QLabel, QLineEdit, QWidget

from calibre_plugins.goodreads_manga_guard import guard

PREFS = JSONConfig('plugins/goodreads_manga_guard')
PREFS.defaults['tags'] = 'Manga'
PREFS.defaults['show_message'] = True


def excluded_tags():
    return guard.parse_tags(PREFS['tags'])


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.tags = QLineEdit(PREFS['tags'], self)
        self.tags.setPlaceholderText('Manga')
        self.show_message = QCheckBox('Show a message in the status bar when books are skipped', self)
        self.show_message.setChecked(PREFS['show_message'])
        layout.addRow('Keep books with these tags out of Goodreads (comma separated)', self.tags)
        layout.addRow('', self.show_message)

        state = guard.STATE
        if state.installed:
            text = 'Guard: ACTIVE. Books skipped so far this session: %d.' % state.skipped_total
        else:
            text = 'Guard: NOT ACTIVE - %s. Manga are NOT being kept out of Goodreads.' % state.reason
        if state.last_problem:
            text += '\nLast problem: %s' % state.last_problem
        status = QLabel(text, self)
        status.setWordWrap(True)
        layout.addRow(status)
        note = QLabel('Changes apply the next time Calibre starts.', self)
        note.setStyleSheet('color: gray; font-style: italic;')
        layout.addRow(note)

    def save_settings(self):
        PREFS['tags'] = self.tags.text().strip() or 'Manga'
        PREFS['show_message'] = bool(self.show_message.isChecked())
