# SPDX-License-Identifier: BSD-3-Clause
"""Install the selected recorded child transport, refusing startup if it cannot be installed."""

import logging
import os

logger = logging.getLogger(__name__)

if os.environ.get('EDI_REFERENCE_TRANSPORT_ROOT'):
    try:
        from recorded_transport import install_from_environment

        install_from_environment()
    except BaseException:
        logger.exception('The recorded transport could not be installed')
        os._exit(97)
