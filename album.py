#!/usr/bin/env python
import readline, curses, pathlib, sys, os, signal, threading, time, tempfile


ITER_DELAY = 0.1


class ThreadMixin:
    _done = _stopped = False

    @property
    def done(self) -> bool:
        return self._done

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self):
        self._stopped = True


class HelpersMixin:
    @staticmethod
    def is_file_type_in(path: pathlib.Path, suffixes: set | list) -> bool:
        return path.is_file() and path.suffix.lower()[1:] in suffixes

    @staticmethod
    def get_w_x_h(cmd: str) -> tuple[int]:
        return map(int, os.popen(cmd).read().split('x'))


class ImagesLoader(threading.Thread, ThreadMixin, HelpersMixin):
    suffixes = {'jpg', 'jpeg', 'png', 'gif', 'tiff', 'webp', 'bmp', 'svg'}

    def run(self):
        callback, path, entry_path = self._args
        index, files = 0, []

        for i in path.glob('**/*'):
            if self._stopped:
                break
            if self.is_file_type_in(i, self.suffixes):
                files.append(i)
            if entry_path and i == entry_path:
                index = len(files) - 1

        self._done = True

        if callback:
            callback(files, index)


class ImageScalerThread(threading.Thread, ThreadMixin, HelpersMixin):
    _scaled: tempfile._TemporaryFileWrapper | None = None
    scaled: pathlib.Path | None = None
    menu_height = 60

    def run(self):
        file, i_height, i_width = self._args
        w_width, w_height = self.get_w_x_h('kitty icat --print-window-size')
        width = w_width if i_width > w_width else i_width
        height = (w_height - self.menu_height) if i_height > (w_height - self.menu_height)  else i_height

        if i_height > (w_height - self.menu_height):
            self._scaled = tempfile.NamedTemporaryFile(suffix=file.suffix)
            self.scaled = pathlib.Path(self._scaled.name)
            proc = os.popen(f'magick "{file}" -resize {width}x{height} "{self._scaled.name}"')._proc

            while proc.poll() is None and not self._stopped:
                time.sleep(ITER_DELAY)

        else:
            self.scaled = file

        self._done = True


class ImageScaler(HelpersMixin):
    _store: dict[str, ImageScalerThread] = {}

    def scale(self, file: pathlib.Path) -> str:
        i_width, i_height = self.get_w_x_h(f'identify -ping -format "%wx%h" "{file}"')
        i_id = f'{file.name}_{i_width}_{i_height}'

        if i_id in self._store:
            return i_id

        self._store[i_id] = ImageScalerThread(args=(file, i_height, i_width))
        self._store[i_id].start()
        return i_id

    def get(self, id: str) -> pathlib.Path:
        return self._store[id].scaled

    def is_done(self, id: str) -> bool:
        return self._store[id].done

    def stop(self, id: str) -> None:
        self._store[id].stop()
        del self._store[id]

    def teardown(self) -> None:
        for thread in self._store.values():
            thread._scaled and thread._scaled.close()

        self._store.clear()


class Album(HelpersMixin):
    exit_keys = {4, 10, 113} # NOTE: enter/q/ctrl+d codes
    scaling_blacklist = {'gif', 'svg'}
 
    _loading = True
    _index = 0
    _files: list[pathlib.Path] = []
    _window: curses.window | None = None
    _loader: ImagesLoader
    _scaler: ImageScaler

    def __init__(self, path: pathlib.Path):
        entry_path = path if path.is_file() else None
        self._scaler = ImageScaler()
        self._loader = ImagesLoader(
            args=(
                self.on_load,
                path.parent if entry_path else path,
                entry_path,
            ),
        )

        signal.signal(signal.SIGWINCH, self.resize)
        self._loader.start()

    def on_load(self, files: list[pathlib.Path], current_idx: int):
        self._files = files
        self._index = current_idx
        displayed = False

        while not displayed and not self._loader.stopped:
            displayed = self.display(True)
            time.sleep(ITER_DELAY)

    def teardown(self):
        self._loader.is_alive() and self._loader.stop()
        self._scaler.teardown()

    def resize(self, *args):
        size = os.get_terminal_size()
        curses.resizeterm(size.lines, size.columns)
        self._window.redrawwin()
        self.display()

    @property
    def current(self) -> pathlib.Path:
        return self._files and self._files[self.index]

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int):
        if value != self._index:
            self._index = value
            self.display()

    @property
    def remaining(self) -> int:
        return len(self._files)-1-self.index

    def has_next(self) -> bool:
        return self.index <= len(self._files)-2

    def has_prev(self) -> bool:
        return self.index > 0

    def goto_next(self):
        if self.has_next():
            self.index += 1

    def goto_prev(self):
        if self.has_prev():
            self.index -= 1

    def goto_first(self):
        self.index = 0

    def goto_last(self):
        self.index = len(self._files)-1

    def get_scaled_current(self) -> pathlib.Path:
        if self.is_file_type_in(self.current, self.scaling_blacklist):
            return self.current

        key = 0
        i_id = self._scaler.scale(self.current)

        while not self._scaler.is_done(i_id) and key not in self.exit_keys:
            key = self._window.getch()
            time.sleep(ITER_DELAY)

        if key in self.exit_keys:
            self._scaler.stop(i_id)
            self.teardown()
            exit()

        return self._scaler.get(i_id)

    def display_loading(self):
        self._window.clear()
        self._window.refresh()
        size = os.get_terminal_size()
        self._window.addstr(size.lines // 2, size.columns // 2, 'Loading...', curses.A_BOLD)
        self._window.addstr(size.lines // 2 + 2, size.columns // 2 - 5, 'Press enter to exit', curses.A_REVERSE)
        self._window.refresh()

    def display(self, hide_err=False) -> pathlib.Path | None:
        self.display_loading()
        current = self.get_scaled_current()
        cmd = f'kitty icat --clear "{current}"' + (' 2> /dev/null' if hide_err else '')

        self._window.erase()
        self._window.refresh()
        if os.system(cmd):
            return

        size = os.get_terminal_size()
        name_limit = size.columns - 43
        name = self.current.name
        name = name if len(name) < name_limit else f'...{name[-name_limit::]}'
        name = f'({name})'

        self._window.refresh()
        self._window.addstr(size.lines - 1, size.columns // 2 - len(name) // 2, name, curses.A_BOLD)

        if self.has_prev():
            self._window.refresh()
            self._window.addstr(size.lines - 1, 1, f' <-({self.index}) ', curses.A_REVERSE)

        if self.has_next():
            self._window.refresh()
            label = f' ({self.remaining})-> '
            self._window.addstr(size.lines - 1, size.columns - (len(label) + 1), label, curses.A_REVERSE)

        return current

    def __call__(self, window: curses.window):
        self._window = window
        key = 0

        curses.use_default_colors()
        curses.curs_set(0)
        window.nodelay(True)
        self.display_loading()

        while key not in self.exit_keys:
            try:
                key = window.getch()
            except KeyboardInterrupt:
                break

            if not self._loader.done:
                continue
            elif key == curses.KEY_RIGHT and self.has_next():
                self.goto_next()
            elif key == curses.KEY_LEFT and self.has_prev():
                self.goto_prev()
            elif key == curses.KEY_END and self.has_next():
                self.goto_last()
            elif key == curses.KEY_HOME and self.has_prev():
                self.goto_first()

            time.sleep(ITER_DELAY)

        self.teardown()


def main(args: list[str]) -> str:
    curses.wrapper(Album(pathlib.Path(args[1] if len(args) > 1 else '.')))


def handle_result(args: list[str], answer: str, target_window_id: int, boss: any) -> None:
    pass


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <path>')
        exit(1)

    path = pathlib.Path(sys.argv[1])

    if not path.exists():
        print(f'Error: {sys.argv[1]} does not exist')
        exit(1)

    curses.wrapper(Album(path))
