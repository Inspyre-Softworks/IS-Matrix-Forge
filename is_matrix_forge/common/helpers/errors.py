from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('common.helpers.errors')



def catch_and_notify(
    exception: Exception,
    operation: str,
    op_args: tuple = (),
    op_kwargs: dict = {},
    logger = MOD_LOGGER,
    log_level = 'error'
) -> None:
    """
    Catch and notify an exception.
    """
    logger.log(
        log_level,
        f'Operation "{operation}" failed with exception: {exception}'
    )
)