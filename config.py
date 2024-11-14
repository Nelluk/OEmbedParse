import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('OEmbedParse', True)

OEmbedParse = conf.registerPlugin('OEmbedParse')

# Global settings
conf.registerGlobalValue(OEmbedParse, 'domains',
    registry.SpaceSeparatedListOfStrings([], """List of domains to monitor for oEmbed data. 
    Add domains using: config plugins.OEmbedParse.domains add domain.com
    Remove domains using: config plugins.OEmbedParse.domains remove domain.com
    List domains using: config plugins.OEmbedParse.domains"""))

# Channel-specific settings
conf.registerChannelValue(OEmbedParse, 'enabled',
    registry.Boolean(False, """Enable OEmbed parsing in this channel. 
    Enable in a channel using: config channel #channel plugins.OEmbedParse.enabled True
    Disable in a channel using: config channel #channel plugins.OEmbedParse.enabled False"""))
