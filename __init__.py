from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

from .sampler_nodes import (NODE_CLASS_MAPPINGS as SAMPLER_CLASSES,
                            NODE_DISPLAY_NAME_MAPPINGS as SAMPLER_NAMES)

from .layout_nodes import (NODE_CLASS_MAPPINGS as LAYOUT_CLASSES,
                           NODE_DISPLAY_NAME_MAPPINGS as LAYOUT_NAMES)

# Copy, do not mutate the legacy module mappings.
NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, **SAMPLER_CLASSES, **LAYOUT_CLASSES}
NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, **SAMPLER_NAMES, **LAYOUT_NAMES}

from .h3draft.frontend_guard import install_frontend_guard
install_frontend_guard()

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
