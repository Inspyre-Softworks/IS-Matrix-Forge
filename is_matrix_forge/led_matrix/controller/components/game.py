from __future__ import annotations

from enum import IntEnum
from typing import Any, Callable, Mapping, Optional, Union

from aliaser import Aliases, alias

from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.controller.errors import (
    LEDMatrixControllerGameNotRunningError,
)
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.hardware import (
    Game,
    GameControlVal,
    GameOfLifeStartParam,
    send_command,
)


def _coerce_game(value: Union[Game, IntEnum, int, str]) -> Game:
    if isinstance(value, Game):
        return value
    if isinstance(value, IntEnum):
        return Game(int(value))
    if isinstance(value, int):
        return Game(value)
    if isinstance(value, str):
        normalized = value.strip().replace('-', '').replace('_', '').replace(' ', '').lower()
        for game in Game:
            game_name = game.name.replace('_', '').lower()
            if game_name == normalized:
                return game
    raise ValueError(f'Unknown game value: {value!r}')


def _coerce_game_control(value: Union[GameControlVal, IntEnum, int, str]) -> GameControlVal:
    if isinstance(value, GameControlVal):
        return value
    if isinstance(value, IntEnum):
        return GameControlVal(int(value))
    if isinstance(value, int):
        return GameControlVal(value)
    if isinstance(value, str):
        normalized = value.strip().replace('-', '').replace('_', '').replace(' ', '').lower()
        for control in GameControlVal:
            if control.name.lower() == normalized:
                return control
    raise ValueError(f'Unknown game control value: {value!r}')


def _coerce_game_payload_value(value: Union[IntEnum, int, str]) -> int:
    if isinstance(value, IntEnum):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.isdigit() or (
            normalized.startswith('-') and normalized[1:].isdigit()
        ):
            return int(normalized)

        key = normalized.lower().replace('-', '').replace('_', '').replace(' ', '')
        for option in GameOfLifeStartParam:
            option_key = option.name.lower().replace('_', '')
            if option_key == key:
                return int(option)

    raise ValueError(f'Unknown game start parameter: {value!r}')


def _normalize_keypress(value: object) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, bytes):
        windows_arrows = {
            b'\xe0H': 'up',
            b'\xe0P': 'down',
            b'\xe0K': 'left',
            b'\xe0M': 'right',
        }
        if value in windows_arrows:
            return windows_arrows[value]
        value = value.decode('utf-8', errors='ignore')

    if not isinstance(value, str):
        value = str(value)

    aliases = {
        '\x1b[A': 'up',
        '\x1b[B': 'down',
        '\x1b[D': 'left',
        '\x1b[C': 'right',
        'arrow_up': 'up',
        'arrow_down': 'down',
        'arrow_left': 'left',
        'arrow_right': 'right',
    }

    key = value.strip()
    if not key:
        return None

    lowered = key.lower()
    if lowered in aliases:
        return aliases[lowered]
    return lowered


def _default_key_reader() -> str:
    try:
        import msvcrt

        first = msvcrt.getwch()
        if first in ('\x00', '\xe0'):
            second = msvcrt.getwch()
            return {
                'H': 'up',
                'P': 'down',
                'K': 'left',
                'M': 'right',
            }.get(second, second)
        return first
    except ImportError:
        import sys
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            first = sys.stdin.read(1)
            if first == '\x1b':
                second = sys.stdin.read(1)
                third = sys.stdin.read(1)
                return first + second + third
            return first
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class GameManager(Aliases):
    """
    Controller mixin for firmware-backed games.

    The running game is tracked on the controller so other mixins can block
    display mutations while the firmware game owns the matrix.
    """

    AVAILABLE_GAMES = Game
    GAME_CONTROLS = GameControlVal
    RAW_GAME_CONTROLS = {
        'up': int(GameControlVal.Up),
        'down': int(GameControlVal.Down),
        'left': int(GameControlVal.Left),
        'right': int(GameControlVal.Right),
        'quit': int(GameControlVal.Quit),
        '2left': 5,
        '2right': 6,
    }
    GAME_START_OPTIONS = GameOfLifeStartParam
    DEFAULT_SNAKE_KEYMAP = {
        'up': GameControlVal.Up,
        'w': GameControlVal.Up,
        'down': GameControlVal.Down,
        's': GameControlVal.Down,
        'left': GameControlVal.Left,
        'a': GameControlVal.Left,
        'right': GameControlVal.Right,
        'd': GameControlVal.Right,
        'q': GameControlVal.Quit,
        'quit': GameControlVal.Quit,
    }

    def __init__(self, **kwargs: Any):
        self._running_game: Optional[Game] = None
        super().__init__(**kwargs)

    @property
    def running_game(self) -> Optional[Game]:
        return self._running_game

    @property
    def game_running(self) -> bool:
        return self._running_game is not None

    def _ensure_game_not_running(self, *, method_name: str) -> None:
        from is_matrix_forge.led_matrix.controller.errors import (
            LEDMatrixControllerGameRunningError,
        )

        if self.game_running:
            raise LEDMatrixControllerGameRunningError(
                method_name=method_name,
                game=self.running_game,
            )

    @alias('play_game')
    @synchronized(allow_when_game_running=True)
    def start_game(
        self,
        game: Union[Game, IntEnum, int, str],
        *parameters: Union[IntEnum, int, str],
    ) -> Game:
        selected_game = _coerce_game(game)

        if getattr(self, 'breathing', False):
            self.breathing = False
        if getattr(self, 'animating', False):
            self.animate(False)

        payload = [int(selected_game)]
        payload.extend(_coerce_game_payload_value(param) for param in parameters)

        send_command(self.device, CommandVals.StartGame, payload)
        self._running_game = selected_game
        return selected_game

    @alias('game_control', 'control_game')
    @synchronized(allow_when_game_running=True)
    def send_game_control(self, control: Union[GameControlVal, IntEnum, int, str]) -> int:
        if isinstance(control, int) and not isinstance(control, IntEnum):
            selected_control = control
        else:
            try:
                selected_control = int(_coerce_game_control(control))
            except ValueError:
                if isinstance(control, str):
                    key = control.strip().lower().replace('-', '').replace('_', '').replace(' ', '')
                    if key in self.RAW_GAME_CONTROLS:
                        selected_control = self.RAW_GAME_CONTROLS[key]
                    else:
                        raise
                else:
                    raise

        if not self.game_running:
            raise LEDMatrixControllerGameNotRunningError(control=selected_control)

        send_command(self.device, CommandVals.GameControl, [selected_control])
        if selected_control == int(GameControlVal.Quit):
            self._running_game = None
        return selected_control

    def play_game_loop(
        self,
        game: Union[Game, IntEnum, int, str],
        *game_parameters: Union[IntEnum, int, str],
        keymap: Optional[Mapping[object, Union[GameControlVal, IntEnum, int, str]]] = None,
        key_reader: Optional[Callable[[], object]] = None,
        ignore_unknown_keys: bool = True,
    ) -> Game:
        active_game = self.start_game(game, *game_parameters)

        reader = key_reader or _default_key_reader
        normalized_keymap = {
            normalized: value
            for raw_key, value in (keymap or {}).items()
            if (normalized := _normalize_keypress(raw_key)) is not None
        }

        while self.game_running:
            raw_key = reader()
            normalized = _normalize_keypress(raw_key)

            if normalized is None:
                continue

            if normalized not in normalized_keymap:
                if ignore_unknown_keys:
                    continue
                raise KeyError(f'No game control is configured for key {raw_key!r}')

            self.send_game_control(normalized_keymap[normalized])

        return active_game

    @alias('play_snake_loop', 'run_snake')
    def play_snake(
        self,
        *,
        keymap: Optional[Mapping[object, Union[GameControlVal, IntEnum, int, str]]] = None,
        key_reader: Optional[Callable[[], object]] = None,
        ignore_unknown_keys: bool = True,
    ) -> Game:
        merged_keymap = dict(self.DEFAULT_SNAKE_KEYMAP)
        if keymap:
            merged_keymap.update(keymap)

        return self.play_game_loop(
            Game.Snake,
            keymap=merged_keymap,
            key_reader=key_reader,
            ignore_unknown_keys=ignore_unknown_keys,
        )
