#!/usr/bin/env python
import unittest, unittest.mock, pathlib

from album import Album


class TestAlbum(unittest.TestCase):
    @unittest.mock.patch('album.ImageScaler')
    @unittest.mock.patch('album.ImagesLoader')
    @unittest.mock.patch('curses.initscr')
    def setUp(self, mock_curses, mock_loader, mock_scaler):
        self.path = pathlib.Path('./test_image.jpg')
        self.album = Album(self.path)
        self.album._window = unittest.mock.MagicMock()
        self.album._files = [unittest.mock.MagicMock()] * 4

        # Mock dependencies
        self.mock_curses = mock_curses
        self.mock_loader = mock_loader.return_value
        self.mock_scaler = mock_scaler.return_value
        self.patch_terminal_size = unittest.mock.patch('album.os.get_terminal_size')
        self.mock_terminal_size = self.patch_terminal_size.start()
        self.addCleanup(self.patch_terminal_size.stop)

    def test_init(self):
        """Test initialization of Album class"""
        self.assertEqual(self.album._index, 0)
        self.assertEqual(self.album._zoom_level, 0)
        self.assertEqual(len(self.album.exit_keys), 3)
        self.assertTrue(isinstance(self.album._scaler, unittest.mock.MagicMock))
        self.mock_loader.start.assert_called_once()
        self.mock_terminal_size.assert_not_called()

    def test_goto_next(self):
        """Test moving to the next image"""
        self.album.goto_next()
        self.assertEqual(self.album.index, 1)
        self.album.goto_next()
        self.assertEqual(self.album.index, 2)
        self.mock_terminal_size.assert_called()

    def test_goto_prev(self):
        """Test moving to the previous image"""
        self.album.index = 2
        self.album.goto_prev()
        self.assertEqual(self.album.index, 1)
        self.album.goto_prev()
        self.assertEqual(self.album.index, 0)
        self.mock_terminal_size.assert_called()

    def test_goto_first(self):
        """Test moving to the first image"""
        self.album.index = 2
        self.album.goto_first()
        self.assertEqual(self.album.index, 0)
        self.mock_terminal_size.assert_called()

    def test_goto_last(self):
        """Test moving to the last image"""
        self.album.index = 1
        self.album.goto_last()
        self.assertEqual(self.album.index, len(self.album._files) - 1)
        self.mock_terminal_size.assert_called()


if __name__ == '__main__':
    unittest.main()
