from __future__ import annotations

import json

import pytest

from is_matrix_forge.led_matrix.controller.components.animation import AnimationManager
from is_matrix_forge.led_matrix.display.animations import Animation


class DummyAnimationManager(AnimationManager):
    """Concrete manager for storage-only tests."""

    pass


def write_animation(path):
    """Write one valid single-frame animation file."""
    grid = [[0 for _ in range(34)] for _ in range(9)]
    path.write_text(json.dumps([{'grid': grid, 'duration': 0.1}]), encoding='utf-8')


def test_animation_manager_creates_and_lists_default_directory(tmp_path):
    """Storage discovery creates its directory and lists JSON stems only."""
    directory = tmp_path / 'animations'
    manager = DummyAnimationManager(animations_dir=directory)
    write_animation(directory / 'Zebra.json')
    write_animation(directory / 'alpha.JSON')
    (directory / 'notes.txt').write_text('ignore me', encoding='utf-8')

    assert directory.is_dir()
    assert manager.list_animation_names() == ['alpha', 'Zebra']
    assert manager.animation_names == ['alpha', 'Zebra']


def test_load_animation_by_name_or_json_filename(tmp_path):
    """Names resolve case-insensitively with or without a JSON suffix."""
    manager = DummyAnimationManager(animations_dir=tmp_path)
    write_animation(tmp_path / 'Pulse.json')

    by_name = manager.load_animation('pulse')
    by_filename = manager.load_animation('Pulse.json', loop=True)

    assert isinstance(by_name, Animation)
    assert len(by_name) == 1
    assert isinstance(by_filename, Animation)
    assert by_filename.loop is True


def test_animation_class_lists_and_loads_by_name(tmp_path):
    """The standalone Animation class shares manager storage semantics."""
    write_animation(tmp_path / 'Standalone.json')

    assert Animation.list_names(tmp_path) == ['Standalone']
    animation = Animation.from_name('standalone', storage_dir=tmp_path)

    assert isinstance(animation, Animation)
    assert len(animation) == 1


@pytest.mark.parametrize('name', ['', '../escape', 'nested/name', 'other.txt'])
def test_load_animation_rejects_unsafe_or_invalid_names(tmp_path, name):
    """Name lookup rejects traversal, subdirectories, and other extensions."""
    manager = DummyAnimationManager(animations_dir=tmp_path)
    with pytest.raises((ValueError, FileNotFoundError)):
        manager.load_animation(name)


def test_load_animation_reports_missing_name(tmp_path):
    """A missing logical animation name reports its configured directory."""
    manager = DummyAnimationManager(animations_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match='missing'):
        manager.load_animation('missing')
