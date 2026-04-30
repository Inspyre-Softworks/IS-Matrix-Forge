from typing import Iterable

import threading
import time
from collections.abc import Callable

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments
from is_matrix_forge.led_matrix.Scripts.led_matrix.guards import run_with_guard
from is_matrix_forge.led_matrix.helpers.location import resolve_controller_location

ARGUMENTS = Arguments()

def _desired_side(cli_args):
    if cli_args is None:
        return None
    if getattr(cli_args, 'only_left', False):
        return 'left'
    if getattr(cli_args, 'only_right', False):
        return 'right'
    return None


def _controller_side(controller):
    side, _ = resolve_controller_location(controller)
    return side

def _slot_rank(controller) -> int:
    """
    Returns an integer for sorting. Unknown becomes 0 (neutral).
    """
    _, slot = resolve_controller_location(controller)
    try:
        return int(slot)
    except (TypeError, ValueError):
        return 0

def find_leftmost_matrix(controllers: Iterable):
    """Return the controller that is physically positioned furthest left.

    Ordering:
      1) left side first, unknown middle, right side last
      2) within same side, lower slot = further left
      3) stable tiebreaker by original index
    """
    ranked = []
    for index, controller in enumerate(controllers):
        side = _controller_side(controller)
        if side == 'left':
            side_rank = 0
        elif side == 'right':
            side_rank = 2
        else:
            side_rank = 1  # unknowns in the middle

        rank_tuple = (side_rank, _slot_rank(controller), index)
        ranked.append((rank_tuple, controller))

    if not ranked:
        return None

    return min(ranked, key=lambda item: item[0])[1]

def find_rightmost_matrix(controllers: Iterable):
    """Return the controller that is physically positioned furthest right.

    Ordering:
      1) right side first, unknown middle, left side last
      2) within same side, higher slot = further right
      3) stable tiebreaker by original index
    """
    ranked = []
    for index, controller in enumerate(controllers):
        side = _controller_side(controller)
        if side == 'right':
            side_rank = 0
        elif side == 'left':
            side_rank = 2
        else:
            side_rank = 1  # unknowns in the middle

        # negate slot so larger slot numbers sort earlier for "rightmost"
        rank_tuple = (side_rank, -_slot_rank(controller), index)
        ranked.append((rank_tuple, controller))

    if not ranked:
        return None

    return min(ranked, key=lambda item: item[0])[1]


def _filter_controllers_by_side(controllers, cli_args):
    """Return the controllers that match the requested keyboard side.

    When ``--only-right`` is requested, returns only the single rightmost
    matrix (via :func:`find_rightmost_matrix`) so that exactly one device is
    targeted even when multiple matrices share the same side.  Likewise for
    ``--only-left``.
    """

    desired = _desired_side(cli_args)

    if desired is None:
        return list(controllers)

    if desired == 'right':
        result = find_rightmost_matrix(controllers)
        return [result] if result is not None else []

    if desired == 'left':
        result = find_leftmost_matrix(controllers)
        return [result] if result is not None else []

    return list(controllers)


def _describe_selection(cli_args):
    desired = _desired_side(cli_args)

    if desired == 'left':
        return 'the leftmost LED matrix'

    if desired == 'right':
        return 'the rightmost LED matrix'

    return 'any LED matrix'


def _order_controllers_for_span(controllers: Iterable):
    controllers = list(controllers)

    if len(controllers) <= 1:
        return controllers

    ordered = []
    remaining = list(controllers)

    while remaining:
        next_controller = find_leftmost_matrix(remaining)

        if next_controller is None:
            ordered.extend(remaining)
            break

        ordered.append(next_controller)
        remaining = [controller for controller in remaining if controller is not next_controller]

    return ordered


def _build_horizontal_span_animations(text: str, controllers: Iterable):
    controllers = list(controllers)

    if not controllers:
        return {}

    from is_matrix_forge.assets.font_map.base import FontMap
    from is_matrix_forge.led_matrix.display.animations.animation import Animation, Frame
    from is_matrix_forge.led_matrix.display.animations.text.glyph_normalizer import GlyphNormalizer
    from is_matrix_forge.led_matrix.display.grid.base import MATRIX_HEIGHT, MATRIX_WIDTH, Grid

    font_map = FontMap(case_sensitive=False)
    case_sensitive = font_map.is_case_sensitive
    normalized_text = text if case_sensitive else text.upper()

    glyphs = []
    normalizer = GlyphNormalizer(MATRIX_WIDTH, MATRIX_HEIGHT)
    for character in normalized_text:
        glyph_rows = font_map.lookup(character)
        normalized_rows = normalizer.normalize(glyph_rows)
        glyphs.append([row[:] for row in normalized_rows])

    spacing = 1
    glyph_widths = [len(glyph[0]) if glyph and glyph[0] else 0 for glyph in glyphs]
    total_glyph_width = sum(glyph_widths) + spacing * (len(glyph_widths) - 1 if glyph_widths else 0)

    segment_width = MATRIX_WIDTH
    total_width = segment_width * len(controllers)
    frame_duration = 0.05

    if total_glyph_width == 0:
        animations = {}

        for controller in controllers:
            blank_columns = [[0] * MATRIX_HEIGHT for _ in range(segment_width)]
            grid = Grid(
                width=segment_width,
                height=MATRIX_HEIGHT,
                init_grid=[column[:] for column in blank_columns],
                align_x='left',
            )
            frame_one = Frame(grid=grid)
            frame_two = Frame(grid=Grid(
                width=segment_width,
                height=MATRIX_HEIGHT,
                init_grid=[column[:] for column in blank_columns],
                align_x='left',
            ))
            animation = Animation(frame_data=[frame_one, frame_two])
            animation.set_all_frame_durations(frame_duration)
            animations[controller] = animation

        return animations

    canvas = [[0] * max(total_glyph_width, 1) for _ in range(MATRIX_HEIGHT)]
    x_cursor = 0

    for glyph, width in zip(glyphs, glyph_widths):
        glyph_height = len(glyph)
        vertical_padding = max((MATRIX_HEIGHT - glyph_height) // 2, 0)

        for row_index in range(glyph_height):
            if width:
                canvas_row = canvas[vertical_padding + row_index]
                canvas_row[x_cursor:x_cursor + width] = glyph[row_index]

        x_cursor += width + spacing

    offsets = range(-total_width, total_glyph_width)
    frame_columns_by_controller = {controller: [] for controller in controllers}

    for offset in offsets:
        window_rows = [
            [canvas[row][offset + column] if 0 <= offset + column < total_glyph_width else 0 for column in range(total_width)]
            for row in range(MATRIX_HEIGHT)
        ]

        window_columns = [
            [window_rows[row][column] for row in range(MATRIX_HEIGHT)]
            for column in range(total_width)
        ]

        for index, controller in enumerate(controllers):
            start = index * segment_width
            end = start + segment_width
            segment = [column[:] for column in window_columns[start:end]]

            if len(segment) < segment_width:
                segment.extend([[0] * MATRIX_HEIGHT for _ in range(segment_width - len(segment))])

            grid = Grid(
                width=segment_width,
                height=MATRIX_HEIGHT,
                init_grid=segment,
                align_x='left',
            )
            frame_columns_by_controller[controller].append(Frame(grid=grid))

    animations = {}

    for controller, frames in frame_columns_by_controller.items():
        animation = Animation(frame_data=frames or [Frame(width=segment_width, height=MATRIX_HEIGHT)])
        animation.set_all_frame_durations(frame_duration)
        animations[controller] = animation

    return animations


def _run_operation(controllers: Iterable, operation: Callable, *, concurrent: bool) -> None:
    """Run an operation against one or more controllers, optionally in parallel."""

    if concurrent and len(controllers) > 1:
        threads = []

        for controller in controllers:
            thread = threading.Thread(target=operation, args=(controller,), daemon=True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        return

    for controller in controllers:
        operation(controller)


def execute_get_controllers(cli_args=None):
    """Return the available controllers honoring any CLI matrix selection.

    Parameters:
        cli_args (Optional[argparse.Namespace]):
            The parsed command-line arguments. When provided, any matrix
            selection flags (``--only-left`` / ``--only-right``) are applied to
            the available controllers.

    Returns:
        List[LEDMatrixController]:
            A list of controller objects, each representing an available LED matrix.
    """
    from is_matrix_forge.led_matrix.controller import get_controllers
    controllers = get_controllers(
        threaded                 = True,
        skip_all_init_animations = True,
        clear_on_init            = True
    )

    if not controllers:
        raise SystemExit('No LED matrices are available.')

    if filtered := _filter_controllers_by_side(controllers, cli_args):
        return filtered

    raise SystemExit(f'No LED matrices matched the requested selection ({_describe_selection(cli_args)}).')


def scroll_text_command(cli_args=ARGUMENTS):
    """
    Invokes the command to scroll text on the LED matrix.

    Parameters:
        cli_args (Optional[Arguments]):
            The object that holds the command-line arguments. This is a subclass of `argparse.ArgumentParser`.
            (Defaults to `ARGUMENTS`)

    Returns:
        None
    """
    from .arguments.commands.scroll_text import DIRECTION_MAP
    controllers = execute_get_controllers(cli_args)

    direction = DIRECTION_MAP[cli_args.direction.strip().lower()]
    text = cli_args.input

    sequential_requested = getattr(cli_args, 'sequential', False) and len(controllers) > 1
    span_requested = getattr(cli_args, 'span_matrices', False) and len(controllers) > 1
    frame_duration = float(getattr(cli_args, 'frame_duration', 0.33))

    span_animations = None

    if span_requested and sequential_requested:
        raise SystemExit('--span-matrices cannot be combined with --sequential.')

    direction_key = cli_args.direction.strip().lower()

    # All cases run all controllers concurrently; the only variation is whether
    # spanning animations are pre-built (horizontal span/sequential) or each
    # controller scrolls independently.
    if span_requested:
        if direction_key != 'h':
            raise SystemExit('--span-matrices requires --direction h.')

        controllers = _order_controllers_for_span(controllers)
        span_animations = _build_horizontal_span_animations(text, controllers)

    elif sequential_requested:
        # Treat all matrices as a single unified screen.
        # For horizontal: build spanning animations so the text flows across all
        # matrices as one wide canvas (text appears once, traversing all panels).
        # For vertical: play the same animation on all matrices concurrently so
        # that the panels act as a single combined display.
        if direction_key == 'h':
            controllers = _order_controllers_for_span(controllers)
            span_animations = _build_horizontal_span_animations(text, controllers)

    def activator(devices, _stop_event):
        def operation(controller):
            controller.keep_alive = True
            if span_animations is not None:
                animation = span_animations.get(controller)
                if animation is None:
                    return
                animation.set_all_frame_durations(frame_duration)
                controller.play_animation(animation)
            else:
                controller.scroll_text(text, direction=direction, frame_duration=frame_duration)

        _run_operation(devices, operation, concurrent=True)

    def invoke(targets, index=None):
        run_with_guard(
            targets,
            run_for=None,
            clear_after=False,
            activator=activator,
            thread_name='scroll-text-guard' if index is None else f'scroll-text-guard-{index}',
        )

    invoke(controllers)


def display_text_command(cli_args):
    """Display static text on the selected LED matrices until interrupted."""
    controllers = execute_get_controllers(cli_args)

    clear_after = not cli_args.skip_clear
    sequential = getattr(cli_args, 'sequential', False) and len(controllers) > 1

    if sequential and cli_args.run_for is None:
        raise SystemExit('--sequential requires --run-for when multiple matrices are targeted.')

    wait_for_interrupt = cli_args.run_for is None
    text = cli_args.text

    concurrent = not sequential

    def activator(devices, _stop_event):
        def operation(controller):
            controller.keep_alive = True
            controller.show_text(text)

        _run_operation(devices, operation, concurrent=concurrent)

    def invoke(targets, index=None):
        run_with_guard(
            targets,
            run_for=cli_args.run_for,
            clear_after=clear_after,
            activator=activator,
            thread_name='display-text-guard' if index is None else f'display-text-guard-{index}',
            wait_for_interrupt=wait_for_interrupt,
        )

    if sequential:
        for index, controller in enumerate(controllers, start=1):
            invoke([controller], index)
    else:
        invoke(controllers)


def identify_matrices_command(cli_args):
    """Run the identification routine on the selected LED matrices.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``identify-matrices`` sub-command.
    """
    controllers = execute_get_controllers(cli_args)

    for controller in controllers:
        controller.identify(
            skip_clear=cli_args.skip_clear,
            duration=float(cli_args.runtime),
            cycles=int(cli_args.cycle_count),
        )


def bootloader_command(cli_args):
    """Reboot the selected matrix into its firmware bootloader.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``bootloader`` sub-command.
    """
    controllers = execute_get_controllers(cli_args)

    for controller in controllers:
        from is_matrix_forge.led_matrix.console import info
        info(f'Entering bootloader on [bold]{controller!r}[/bold] …')
        controller.jump_to_bootloader()


def install_presets_command(cli_args):
    """Download and install preset files, then remove the legacy data directory.

    When ``--app-dir`` is provided explicitly the derived preset directory
    (``<app-dir>/presets``) is saved to ``settings.json`` so future runs (and
    the startup check) use it.  When ``--app-dir`` is *not* provided the
    installer uses the currently-configured ``presets_dir`` directly, so a
    user who previously ran ``set-presets-dir`` always gets files installed to
    the right place — even if that place is outside the default app-data tree.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``install-presets`` sub-command.
    """
    from is_matrix_forge.led_matrix.Scripts.install_presets.main import PresetInstaller
    from is_matrix_forge.led_matrix.constants import GITHUB_REQ_HEADERS as REQ_HEADERS
    from is_matrix_forge.common.preset_config import get_preset_config
    from pathlib import Path

    config = get_preset_config()

    # If the caller supplied an explicit --app-dir, persist it as the new
    # preset location (which may trigger a file-move via the setter).
    if cli_args.app_dir is not None:
        requested_presets_dir = Path(cli_args.app_dir) / 'presets'
        if requested_presets_dir != config.presets_dir:
            config.presets_dir = requested_presets_dir

    installer = PresetInstaller(
        url=cli_args.url,
        headers=REQ_HEADERS,
        presets_dir=config.presets_dir,
        overwrite_existing=cli_args.overwrite,
        with_progress=getattr(cli_args, 'with_progress', True),
    )
    exit_code = installer.run()
    if isinstance(exit_code, int) and exit_code != 0:
        raise SystemExit(exit_code)


def scroll_until_command(cli_args):
    """Scroll text on the selected matrix until an external command finishes.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``scroll-until`` sub-command.
    """
    import subprocess
    import shlex

    controllers = execute_get_controllers(cli_args)
    text = cli_args.input
    on_complete = getattr(cli_args, 'on_complete', 'clear')

    try:
        cmd = shlex.split(cli_args.command)
    except ValueError as exc:
        from is_matrix_forge.led_matrix.console import error
        error(f'Invalid command string: {exc}')
        raise SystemExit(1) from exc

    # Launch the external process before scrolling starts so its clock
    # includes any matrix initialisation time.
    proc = subprocess.Popen(cmd)  # noqa: S603 – user-supplied command is intentional

    stop_event = threading.Event()

    def _watch_process() -> None:
        proc.wait()
        stop_event.set()

    watcher = threading.Thread(
        target=_watch_process,
        daemon=True,
        name='scroll-until-watcher',
    )
    watcher.start()

    def _scroll_loop(controller) -> None:
        controller.keep_alive = True
        while not stop_event.is_set():
            controller.scroll_text(text)
            # Safety pause: if scroll_text returns unexpectedly fast (e.g.
            # due to an error) avoid a tight busy-wait that consumes the CPU.
            if not stop_event.is_set():
                stop_event.wait(timeout=0.05)

    scroll_threads = []
    for controller in controllers:
        t = threading.Thread(target=_scroll_loop, args=(controller,), daemon=True)
        t.start()
        scroll_threads.append((controller, t))

    try:
        while not stop_event.is_set():
            stop_event.wait(timeout=0.2)
    except KeyboardInterrupt:
        proc.terminate()
        stop_event.set()

    for _, t in scroll_threads:
        t.join(timeout=5.0)

    # Disable keep-alive on every controller
    for controller in controllers:
        try:
            controller.keep_alive = False
        except Exception:
            pass

    if on_complete == 'clear':
        for controller in controllers:
            try:
                controller.clear()
            except Exception:
                pass

    elif on_complete == 'fade':
        for controller in controllers:
            try:
                current_brightness = getattr(controller, 'brightness', 100) or 100
                steps = 20
                for step in range(steps, -1, -1):
                    pct = int(current_brightness * step / steps)
                    try:
                        controller.set_brightness(pct)
                    except Exception:
                        break
                    time.sleep(0.05)
                controller.clear()
            except Exception:
                pass

    # 'leave': nothing to do – display stays as-is


def set_presets_dir_command(cli_args):
    """Move presets to a new directory and save the setting.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``set-presets-dir`` sub-command.
    """
    from pathlib import Path
    from is_matrix_forge.common.preset_config import get_preset_config

    new_path = Path(cli_args.path).expanduser().resolve()
    config = get_preset_config()
    old_path = config.presets_dir

    if new_path == old_path:
        from is_matrix_forge.led_matrix.console import info
        info(f'Presets directory is already set to: [bold]{new_path}[/bold]')
        return

    config.presets_dir = new_path  # moves files and saves setting
    from is_matrix_forge.led_matrix.console import success
    success(f'Presets directory updated: [dim]{old_path}[/dim] → [bold]{new_path}[/bold]')


def show_presets_dir_command(cli_args):
    """Print the currently configured preset directory.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``show-presets-dir`` sub-command.
    """
    from is_matrix_forge.common.preset_config import get_preset_config
    from is_matrix_forge.led_matrix.console import CONSOLE
    from rich.panel import Panel
    from rich import box

    config = get_preset_config()
    presets_dir = config.presets_dir
    has_presets = config.has_presets()

    status = (
        '[bold green]✔ Presets present[/bold green]'
        if has_presets
        else '[bold yellow]⚠ No preset files found[/bold yellow]'
    )
    # Wrap the path in an OSC-8 hyperlink so terminals that support it
    # (e.g. iTerm2, Windows Terminal, GNOME Terminal) open the folder on click.
    file_url = presets_dir.as_uri()  # produces "file:///..."
    body = (
        f'[bold white][link={file_url}]{presets_dir}[/link][/bold white]\n'
        f'{status}'
    )
    CONSOLE.print(
        Panel(
            body,
            title='[bold cyan]\\[IS-Matrix-Forge] Presets Directory[/bold cyan]',
            border_style='cyan',
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def main(cli_args=ARGUMENTS):
    """
    Parses and handles command-line arguments, registering specific subcommands
    and executing associated functions.

    Parameters:
        cli_args (Optional[Arguments]):
            An object containing the command-line parser and associated
            subcommand configurations. (Defaults to `ARGUMENTS`)
    """
    parser_bindings = (
        ('scroll_parser',             'Scroll text command parser was not initialized.',          scroll_text_command),
        ('identify_parser',           'Identify matrices command parser was not initialized.',    identify_matrices_command),
        ('display_parser',            'Display text command parser was not initialized.',         display_text_command),
        ('bootloader_parser',         'Bootloader command parser was not initialized.',           bootloader_command),
        ('install_presets_parser',    'Install-presets command parser was not initialized.',      install_presets_command),
        ('scroll_until_parser',       'Scroll-until command parser was not initialized.',         scroll_until_command),
        ('set_presets_dir_parser',    'Set-presets-dir command parser was not initialized.',      set_presets_dir_command),
        ('show_presets_dir_parser',   'Show-presets-dir command parser was not initialized.',     show_presets_dir_command),
    )

    for attr_name, error_message, handler in parser_bindings:
        parser = getattr(cli_args, attr_name)
        if parser is None:
            raise RuntimeError(error_message)
        parser.set_defaults(func=handler)

    # Parse command-line arguments;
    parsed = cli_args.parse()

    # Run the function associated with the parsed command;
    parsed.func(parsed)


if __name__ == '__main__':
    main()


