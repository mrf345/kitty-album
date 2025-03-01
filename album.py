#!/usr/bin/env python
import readline, curses, pathlib, sys, os, signal, threading, time, tempfile


ITER_DELAY = 0.1


class ThreadMixin:
    _done = _stopped = False

    @property
    def done(self) -> bool:
        """Return whether the thread has completed its execution."""
        return self._done

    @property
    def stopped(self) -> bool:
        """Return whether the thread has been stopped."""
        return self._stopped

    def stop(self):
        """Set the stopped flag to True, signaling the thread to stop."""
        self._stopped = True


class HelpersMixin:
    @staticmethod
    def is_file_type_in(path: pathlib.Path, suffixes: set | list) -> bool:
        """
        Check if the given path is a file and has one of the specified suffixes.

        Args:
            path (pathlib.Path): The path to check.
            suffixes (set | list): A collection of suffixes to compare against.

        Returns:
            bool: True if the file matches any of the suffixes, False otherwise.
        """
        return path.is_file() and path.suffix.lower()[1:] in suffixes

    @staticmethod
    def get_w_x_h(cmd: str) -> tuple[int]:
        """
        Execute a command to get window dimensions.

        Args:
            cmd (str): The command to execute.

        Returns:
            tuple[int]: A tuple containing the width and height of the window.
        """
        return map(int, os.popen(cmd).read().split('x'))


class ImagesLoader(threading.Thread, ThreadMixin, HelpersMixin):
    """
    A thread that loads image files from a specified path and invokes a callback with the list of images.
    """
    suffixes = {'jpg', 'jpeg', 'png', 'gif', 'tiff', 'webp', 'bmp', 'svg'}

    def run(self):
        """
        Run the image loading process.
        """
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
    """
    A thread that scales an image to fit within the terminal window size.
    """
    _scaled: tempfile._TemporaryFileWrapper | None = None
    scaled: pathlib.Path | None = None
    menu_height = 60

    def run(self):
        """
        Run the image scaling process.
        """
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
    """
    Manages image scaling threads, caching scaled images to avoid redundant processing.
    """
    _store: dict[str, ImageScalerThread] = {}

    def scale(self, file: pathlib.Path) -> str:
        """
        Scale an image and return a unique identifier for the scaled image.

        Args:
            file (pathlib.Path): The path to the image file.

        Returns:
            str: A unique identifier for the scaled image.
        """
        i_width, i_height = self.get_w_x_h(f'identify -ping -format "%wx%h" "{file}"')
        i_id = f'{file.name}_{i_width}_{i_height}'

        if i_id in self._store:
            return i_id

        self._store[i_id] = ImageScalerThread(args=(file, i_height, i_width))
        self._store[i_id].start()
        return i_id

    def get(self, id: str) -> pathlib.Path:
        """
        Get the scaled image path for a given identifier.

        Args:
            id (str): The unique identifier of the scaled image.

        Returns:
            pathlib.Path: The path to the scaled image.
        """
        return self._store[id].scaled

    def is_done(self, id: str) -> bool:
        """
        Check if the scaling process for a given identifier has completed.

        Args:
            id (str): The unique identifier of the scaled image.

        Returns:
            bool: True if the scaling is done, False otherwise.
        """
        return self._store[id].done

    def stop(self, id: str) -> None:
        """
        Stop the scaling thread for a given identifier and remove it from the store.

        Args:
            id (str): The unique identifier of the scaled image.
        """
        self._store[id].stop()
        del self._store[id]

    def teardown(self) -> None:
        """
        Clean up all temporary files and stop all scaling threads.
        """
        for thread in self._store.values():
            thread._scaled and thread._scaled.close()

        self._store.clear()


class Album(HelpersMixin):
    """
    Manages the album viewing interface using curses, displaying images from a specified directory.
    """
    exit_keys = {4, 10, 113} # NOTE: enter/q/ctrl+d codes
    scaling_blacklist = {'gif', 'svg'}
 
    _loading = True
    _index = 0
    _files: list[pathlib.Path] = []
    _window: curses.window | None = None
    _loader: ImagesLoader
    _scaler: ImageScaler

    def __init__(self, path: pathlib.Path):
        """
        Initialize the Album instance.

        Args:
            path (pathlib.Path): The path to the directory or image file.
        """
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
        """
        Callback function invoked when image loading is complete.

        Args:
            files (list[pathlib.Path]): The list of loaded image paths.
            current_idx (int): The index of the currently selected image.
        """
        self._files = files
        self._index = current_idx
        displayed = False

        while not displayed and not self._loader.stopped:
            displayed = self.display(True)
            time.sleep(ITER_DELAY)

    def teardown(self):
        """
        Clean up resources, stopping the loader and scaler.
        """
        self._loader.is_alive() and self._loader.stop()
        self._scaler.teardown()

    def resize(self, *args):
        """
        Handle terminal resize events by resizing the curses window.
        """
        size = os.get_terminal_size()
        curses.resizeterm(size.lines, size.columns)
        self._window.redrawwin()
        self.display()

    @property
    def current(self) -> pathlib.Path:
        """
        Get the currently selected image path.

        Returns:
            pathlib.Path: The path to the current image.
        """
        return self._files[self.index]

    @property
    def index(self) -> int:
        """
        Get the index of the currently selected image.

        Returns:
            int: The index of the current image.
        """
        return self._index

    @index.setter
    def index(self, value: int):
        """
        Set the index of the currently selected image and refresh the display.

        Args:
            value (int): The new index for the selected image.
        """
        if value != self._index:
            self._index = value
            self.display()

    @property
    def remaining(self) -> int:
        """
        Get the number of images remaining after the current one.

        Returns:
            int: The count of remaining images.
        """
        return len(self._files)-1-self.index

    def has_next(self) -> bool:
        """
        Check if there is a next image to view.

        Returns:
            bool: True if there is a next image, False otherwise.
        """
        return len(self._files) > 1 and self.index <= len(self._files)-2

    def has_prev(self) -> bool:
        """
        Check if there is a previous image to view.

        Returns:
            bool: True if there is a previous image, False otherwise.
        """
        return self.index > 0

    def goto_next(self):
        """
        Move to the next image if available.
        """
        if self.has_next():
            self.index += 1

    def goto_prev(self):
        """
        Move to the previous image if available.
        """
        if self.has_prev():
            self.index -= 1

    def goto_first(self):
        """
        Move to the first image in the album.
        """
        self.index = 0

    def goto_last(self):
        """
        Move to the last image in the album.
        """
        self.index = len(self._files)-1

    def get_scaled_current(self) -> pathlib.Path:
        """
        Get the scaled version of the current image.

        Returns:
            pathlib.Path: The path to the scaled image.
        """
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
        """
        Display a loading message while images are being loaded.
        """
        self._window.clear()
        self._window.refresh()
        size = os.get_terminal_size()
        self._window.addstr(size.lines // 2, size.columns // 2, 'Loading...', curses.A_BOLD)
        self._window.addstr(size.lines // 2 + 2, size.columns // 2 - 5, 'Press enter to exit', curses.A_REVERSE)
        self._window.refresh()
        self.display_next_and_prev(muted=True)

    def display_next_and_prev(self, muted=False):
        """
        Display navigation options for the next and previous images.

        Args:
            muted (bool): If True, dim the navigation indicators.
        """
        size = os.get_terminal_size()

        self._window.refresh()
        self._window.addstr(
            size.lines - 1,
            1,
            f' <-({self.index}) ',
            curses.A_ITALIC if muted or not self.has_prev() else curses.A_REVERSE,
        )

        self._window.refresh()
        label = f' ({self.remaining})-> '
        self._window.addstr(
            size.lines - 1,
            size.columns - (len(label) + 1),
            label,
            curses.A_ITALIC if muted or not self.has_next() else curses.A_REVERSE
        )

    def display(self, hide_err=False) -> pathlib.Path | None:
        """
        Display the current image and handle user navigation.

        Args:
            hide_err (bool): If True, suppress error messages during image display.

        Returns:
            pathlib.Path | None: The path to the displayed image.
        """
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
        self.display_next_and_prev()

        return current

    def __call__(self, window: curses.window):
        """
        Main entry point for the album viewer.

        Args:
            window (curses.window): The curses window used for displaying images.
        """
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
