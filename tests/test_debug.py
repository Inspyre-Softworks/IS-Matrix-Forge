"""Tests for is_matrix_forge.dev_tools.debug – specifically for is_debug_mode().

These tests verify the fix for the 'Permission denied' crash that occurred when
MARAUDER_FILE_PATH was a directory (because get_debug_mode_keyfile_path()
previously returned user_data_path instead of user_data_path / filename).
"""

from __future__ import annotations




# ---------------------------------------------------------------------------
# is_debug_mode – exception handling
# ---------------------------------------------------------------------------

class TestIsDebugMode:
    def _get_fn(self):
        """Import lazily so the module cache is fresh for each test."""
        from is_matrix_forge.dev_tools.debug import is_debug_mode
        return is_debug_mode

    def test_returns_false_when_file_missing(self, tmp_path):
        is_debug_mode = self._get_fn()
        missing = tmp_path / 'no_such_file.map'
        assert is_debug_mode(missing) is False

    def test_returns_false_when_path_is_directory(self, tmp_path):
        """Regression: open(directory) raises PermissionError on Windows /
        IsADirectoryError on Linux.  Both must be caught, returning False."""
        is_debug_mode = self._get_fn()
        # tmp_path itself is a directory.
        assert is_debug_mode(tmp_path) is False

    def test_returns_false_when_file_has_wrong_content(self, tmp_path):
        is_debug_mode = self._get_fn()
        f = tmp_path / 'marauder.map'
        f.write_text('Mischief Managed.')
        assert is_debug_mode(f) is False

    def test_returns_true_when_file_has_correct_content(self, tmp_path):
        is_debug_mode = self._get_fn()
        f = tmp_path / 'marauder.map'
        f.write_text('I solemnly swear that I am up to no good.')
        assert is_debug_mode(f) is True

    def test_returns_true_when_file_has_correct_content_with_whitespace(self, tmp_path):
        """Content is stripped before comparison."""
        is_debug_mode = self._get_fn()
        f = tmp_path / 'marauder.map'
        f.write_text('  I solemnly swear that I am up to no good.  \n')
        assert is_debug_mode(f) is True


# ---------------------------------------------------------------------------
# get_debug_mode_keyfile_path – must return a file path, not a directory
# ---------------------------------------------------------------------------

class TestGetDebugModeKeyfilePath:
    def test_path_ends_with_filename(self):
        """get_debug_mode_keyfile_path() must return a path that ends with
        DEBUG_MODE_KEYFILE_NAME, not the bare directory."""
        from is_matrix_forge.dev_tools.debug import (
            get_debug_mode_keyfile_path,
            DEBUG_MODE_KEYFILE_NAME,
        )
        path = get_debug_mode_keyfile_path()
        assert path.name == DEBUG_MODE_KEYFILE_NAME, (
            f"Expected filename {DEBUG_MODE_KEYFILE_NAME!r}, "
            f"got {path.name!r} (full path: {path})"
        )

    def test_marauder_file_path_is_not_a_directory(self):
        """The module-level MARAUDER_FILE_PATH constant must not be a bare
        directory.  If it were, open() on it would raise PermissionError /
        IsADirectoryError instead of FileNotFoundError."""
        from is_matrix_forge.dev_tools.debug import (
            MARAUDER_FILE_PATH,
            DEBUG_MODE_KEYFILE_NAME,
        )
        assert MARAUDER_FILE_PATH.name == DEBUG_MODE_KEYFILE_NAME, (
            f"MARAUDER_FILE_PATH {MARAUDER_FILE_PATH} appears to be a directory, "
            f"not a file.  Expected it to end with {DEBUG_MODE_KEYFILE_NAME!r}."
        )
