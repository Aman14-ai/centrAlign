from playwright.sync_api import sync_playwright,Page,Browser,BrowserContext


# Singleton — one instance shared everywhere.

# Lazy start — the browser only launches on first tool use.

# Explicit stop — we can clean up at the end of a run.

# headless=True — no visible window. Change to False while debugging if you want to watch.

# singleton design pattern
class BrowserSession:
    _instance = None

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @classmethod
    def get(cls) -> "BrowserSession":
        if cls._instance is None:
            cls._instance = cls() # if no instance create one
        return cls._instance

    def start(self):
        if self._browser is not None:
            return
        self._playwright = sync_playwright().start() # start playwright engine 
        self._browser = self._playwright.chromium.launch(headless=True) # launches chromium
        self._context = self._browser.new_context() # create an isolated browser session
        self._page = self._context.new_page() # opens a tab in that session

    def page(self) -> Page:
        if self._page is None:
            self.start()
        return self._page

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
