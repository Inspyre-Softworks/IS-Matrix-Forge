import PySimpleGUI as sg


def build_button_grid(num_cols, num_rows, button_size=(1, 1), pad=(1, 1)):
    """
    Returns a list of `num_cols` lists, each containing `num_rows` buttons.
    So: 9 columns of 34 rows each.
    """
    return [
        [sg.Button(' ', key=(col, row), size=button_size, pad=pad)]
         for row in range(num_rows)
    ],
        for col in range(num_cols)
    ]

