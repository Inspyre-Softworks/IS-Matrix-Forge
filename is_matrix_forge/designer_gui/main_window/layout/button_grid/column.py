import PySimpleGUI as sg


def build_grid_frame(num_cols=9, num_rows=34, button_size=(2,1), pad=(1,1)):
    """Return a layout of 9 vertical columns (of 34 buttons each), side by side."""
    return [
        [
            sg.Column(
                [
                    [sg.Button(' ', key=(col, row), size=button_size, pad=pad)]
                    for row in range(num_rows)
                ],
                pad=(0,0)
            )
            for col in range(num_cols)
        ]
    ]
