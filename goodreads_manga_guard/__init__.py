from calibre.customize import InterfaceActionBase


class GoodreadsMangaGuard(InterfaceActionBase):
    name = 'Goodreads Manga Guard'
    description = ('Keeps books tagged Manga out of Goodreads Sync progress updates, including the '
                   'automatic update Kobo Utilities triggers after storing reading positions.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'coder-eb'
    version = (0, 1, 0)
    minimum_calibre_version = (5, 0, 0)
    actual_plugin = 'calibre_plugins.goodreads_manga_guard.action:GoodreadsMangaGuardAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.goodreads_manga_guard.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
