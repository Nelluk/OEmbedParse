"""
OEmbedParse: A Limnoria plugin to parse oEmbed data for specified URL domains posted in an IRC channel.

This plugin monitors IRC messages for URLs from configured domains, fetches their oEmbed data,
and responds with formatted content information. If oEmbed data is unavailable, it falls back
to fetching the page title (if enabled in configuration).

Configuration:
    - domains: List of domains to monitor for oEmbed data
    - enableTitleFallback: Whether to fall back to page title when oEmbed fails
    - maxTitleLength: Maximum length of displayed titles
    - enabled: Enable/disable the plugin per channel

Example usage:
    1. Configure domains:
        !config plugins.OEmbedParse.domains add bsky.app
    2. Enable title fallback:
        !config plugins.OEmbedParse.enableTitleFallback True
    3. Set max title length:
        !config plugins.OEmbedParse.maxTitleLength 200
    4. Enable in channel:
        !config channel plugins.OEmbedParse.enabled True
"""

import supybot
import supybot.world as world

__version__ = "1.0.0"
__author__ = supybot.Author("Chris Steven", "cbsteven@example.com", "https://github.com/cbsteven")
__contributors__ = {}
__url__ = 'https://github.com/cbsteven/OEmbedParse'

from . import config
from . import plugin
from importlib import reload
reload(config)
reload(plugin)

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure
