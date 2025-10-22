
from typing import Iterable, Optional, Tuple

import threading
from collections.abc import Callable

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments
from is_matrix_forge.led_matrix.Scripts.led_matrix.guards import run_with_guard
# from is_matrix_forge.led_matrix.Scripts.identify_matrices import

ARGUMENTS = Arguments()


def _normalize_side(value):
    if isinstance(value, str):
        return value.strip().lower()
    return None

def _desired_side(cli_args):
    if cli_args is None:
        return None
    if getattr(cli_args, 'only_left', False):
        return 'left'
    if getattr(cli_args, 'only_right', False):
        return 'right'
    return None

def _resolve_location(controller) -> Tuple[Optional[str], Optional[int]]:
    """
    Return a normalized (side, slot) tuple from a controller.

    Looks in this order:
      1) Explicit attributes: controller.side_of_keyboard, controller.slot
      2) controller.location if it's a dict with 'side'/'slot'
      3) controller.location if it's a dict with 'abbrev' (e.g. 'L0', 'R2')
      4) controller.location if it's a str, resolved via SLOT_MAP
    """
    # 1) explicit attributes
    side = _normalize_side(getattr(controller, 'side_of_keyboard', None))
    slot = getattr(controller, 'slot', None)

    location = getattr(controller, 'location', None)

    # 2) dict with 'side'/'slot'
    if isinstance(location, dict):
        if side is None:
            side = _normalize_side(location.get('side'))
        if slot is None:
            slot = location.get('slot')

        # 3) dict with 'abbrev' like 'L0', 'R1'
        if (side is None or slot is None) and 'abbrev' in location and isinstance(location['abbrev'], str):
            abbrev = location['abbrev'].strip().upper()
            # Try SLOT_MAP first, then parse fallback
            try:
                from is_matrix_forge.led_matrix.constants import SLOT_MAP
            except Exception:
                SLOT_MAP = {}

            entry = SLOT_MAP.get(abbrev) or {}
            side = _normalize_side(side or entry.get('side'))
            slot = slot if slot is not None else entry.get('slot')

            if (side is None or slot is None):
                # Parse e.g. 'L0'/'R12' -> ('left'/'right', 0/12)
                if len(abbrev) >= 2 and abbrev[0] in ('L', 'R') and abbrev[1:].isdigit():
                    side = _normalize_side(side or ('left' if abbrev[0] == 'L' else 'right'))
                    slot = slot if slot is not None else int(abbrev[1:])

    # 4) location is a string -> SLOT_MAP lookup
    if (side is None or slot is None) and isinstance(location, str):
        try:
            from is_matrix_forge.led_matrix.constants import SLOT_MAP
        except Exception:
            SLOT_MAP = {}
        entry = SLOT_MAP.get(location, {})
        side = _normalize_side(side or entry.get('side'))
        slot = slot if slot is not None else entry.get('slot')

    # normalize slot
    try:
        slot = int(slot) if slot is not None else None
    except (TypeError, ValueError):
        slot = None

    return side, slot


def _controller_side(controller) -> Optional[str]:
    side, _ = _resolve_location(controller)
    return side

def _slot_rank(controller) -> int:
    """
    Returns an integer for sorting. Unknown becomes 0 (neutral).
    """
    _, slot = _resolve_location(controller)
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
        print(f'Ranks: {rank_tuple[0]}, {rank_tuple[1]}, {rank_tuple[2]}')
        ranked.append((rank_tuple, controller))
        print(ranked)

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
        print(f'Ranks: {rank_tuple[0]}, {-rank_tuple[1]}, {rank_tuple[2]}')
        ranked.append((rank_tuple, controller))
        print(ranked)

    if not ranked:
        return None

    return min(ranked, key=lambda item: item[0])[1]


def _filter_controllers_by_side(controllers, cli_args):
    """Return the controllers that match the requested keyboard side."""

    desired = _desired_side(cli_args)

    if desired is None:
        return list(controllers)

    return [
        controller for controller in controllers
        if _controller_side(controller) == desired
    ]


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

    origin = find_rightmost_matrix(controllers)

    if origin is None:
        return controllers

    ordered = [origin]
    remaining = [controller for controller in controllers if controller is not origin]

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

    span_animations = None

    if span_requested:
        if cli_args.direction.strip().lower() != 'h':
            raise SystemExit('--span-matrices requires --direction h.')

        if sequential_requested:
            raise SystemExit('--span-matrices cannot be combined with --sequential.')

        controllers = _order_controllers_for_span(controllers)
        span_animations = _build_horizontal_span_animations(text, controllers)
        sequential = False
        concurrent = True
    else:
        sequential = sequential_requested
        concurrent = not sequential

    def activator(devices, _stop_event):
        def operation(controller):
            controller.keep_alive = True
            if span_animations is not None:
                animation = span_animations.get(controller)
                if animation is None:
                    return
                controller.play_animation(animation)
            else:
                controller.scroll_text(text, direction=direction)

        _run_operation(devices, operation, concurrent=concurrent)

    def invoke(targets, index=None):
        run_with_guard(
            targets,
            run_for=None,
            clear_after=False,
            activator=activator,
            thread_name='scroll-text-guard' if index is None else f'scroll-text-guard-{index}',
        )

    if sequential:
        for index, controller in enumerate(controllers, start=1):
            invoke([controller], index)
    else:
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


def main(cli_args=ARGUMENTS):
    """
    Parses and handles command-line arguments, registering specific subcommands
    and executing associated functions.

    This function sets up a command-line interface (CLI) parser, registers a
    specific subcommand (`scroll-text`), and associates a function (`scroll_text_command`)
    with this subcommand. After parsing the arguments, it executes the appropriate
    function based on the parsed subcommand.

    Parameters:
        cli_args (Optional[Arguments]):
            An object containing the command-line parser and associated
            subcommand configurations. It must have attributes `scroll_parser`
            and a callable `parse` function. (Defaults to `ARGUMENTS`)
    """
    parser_bindings = (
        ('scroll_parser', 'Scroll text command parser was not initialized.', scroll_text_command),
        ('identify_parser', 'Identify matrices command parser was not initialized.', identify_matrices_command),
        ('display_parser', 'Display text command parser was not initialized.', display_text_command),
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


