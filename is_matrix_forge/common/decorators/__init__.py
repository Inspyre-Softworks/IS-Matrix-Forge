from inspyre_toolbox.syntactic_sweets.classes.decorators import validate_type
from is_matrix_forge.common.decorators.freeze_setter import freeze_setter
from is_matrix_forge.led_matrix.errors.misc import ImplicitNameDerivationError
from aliaser import Aliases


__all__ = [
    'Aliases',
    'ImplicitNameDerivationError',
    'freeze_setter',
    'validate_type',
]
