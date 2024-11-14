import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('OEmbedParse', True)

OEmbedParse = conf.registerPlugin('OEmbedParse')

conf.registerGlobalValue(OEmbedParse, 'domains',
    registry.SpaceSeparatedListOfStrings([], """List of domains to monitor for oEmbed data."""))

conf.registerGlobalValue(OEmbedParse, 'enableTitleFallback',
    registry.Boolean(True, """Enable falling back to page title when oEmbed data is unavailable."""))

conf.registerGlobalValue(OEmbedParse, 'maxTitleLength',
    registry.PositiveInteger(200, """Maximum length of title to display."""))

conf.registerChannelValue(OEmbedParse, 'enabled',
    registry.Boolean(True, """Enable OEmbed parsing in this channel."""))
