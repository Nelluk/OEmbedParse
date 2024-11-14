import re
import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
from supybot import callbacks, conf, ircmsgs, log, utils, world
from supybot.commands import *

class OEmbedParse(callbacks.Plugin):
    """
    A Limnoria plugin to parse oEmbed data for specified URL domains posted in an IRC channel.
    
    This plugin listens for messages in configured channels, extracts URLs from these messages,
    and checks if they belong to domains specified in the plugin's configuration. If a matching
    domain is found, it attempts to retrieve and parse oEmbed data for the URL. If oEmbed data is
    unavailable or an error occurs, the plugin fetches the webpage's <title> as a fallback.
    """
    threaded = True

    def __init__(self, irc):
        self.__parent = super(OEmbedParse, self)
        self.__parent.__init__(irc)
        
    def _extract_urls(self, text):
        """Extract URLs from text using regex."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        log.debug(f'OEmbedParse: Found URLs in message: {urls}')
        return urls

    def _get_domain(self, url):
        """Extract domain from URL."""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        log.debug(f'OEmbedParse: Extracted domain {domain} from URL {url}')
        return domain

    def _is_monitored_domain(self, domain):
        """Check if domain is in the configured list."""
        monitored_domains = self.registryValue('domains')
        is_monitored = domain in monitored_domains
        log.debug(f'OEmbedParse: Domain {domain} monitored status: {is_monitored}')
        return is_monitored

    def _fetch_oembed_data(self, url):
        """Fetch oEmbed data for a given URL."""
        try:
            log.debug(f'OEmbedParse: Fetching page content for {url}')
            # Fetch the webpage
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            log.debug(f'OEmbedParse: Parsing page content with BeautifulSoup')
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug log the first 500 chars of HTML
            log.debug(f'OEmbedParse: Page HTML preview: {response.text[:500]}...')

            # Look for oEmbed link
            oembed_link = soup.find('link', type=re.compile(r'application\/(json|xml)\+oembed'))
            if not oembed_link:
                log.debug('OEmbedParse: No oEmbed link found in page')
                return None

            # Log found oEmbed link
            log.debug(f'OEmbedParse: Found oEmbed link: {oembed_link}')

            # Fetch oEmbed data
            oembed_url = oembed_link.get('href')
            log.debug(f'OEmbedParse: Fetching oEmbed data from {oembed_url}')
            
            oembed_response = requests.get(oembed_url, timeout=10)
            oembed_response.raise_for_status()
            
            oembed_data = oembed_response.json()
            log.debug(f'OEmbedParse: Received oEmbed data: {json.dumps(oembed_data, indent=2)}')
            
            return oembed_data

        except Exception as e:
            log.error(f'OEmbedParse: Error fetching oEmbed data: {str(e)}')
            return None

    def _get_page_title(self, url):
        """Fetch page title as fallback."""
        try:
            log.debug(f'OEmbedParse: Attempting title fallback for {url}')
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else None
            
            if title:
                max_length = self.registryValue('maxTitleLength')
                title = title.strip()
                original_length = len(title)
                
                if len(title) > max_length:
                    title = title[:max_length - 3] + '...'
                    log.debug(f'OEmbedParse: Title truncated from {original_length} to {max_length} chars')
                
                log.debug(f'OEmbedParse: Found page title: {title}')
            else:
                log.debug('OEmbedParse: No title found in page')
                
            return title
            
        except Exception as e:
            log.error(f'OEmbedParse: Error fetching page title: {str(e)}')
            return None

    def _format_oembed_response(self, data):
        """Format oEmbed data for IRC response."""
        log.debug(f'OEmbedParse: Formatting oEmbed data: {json.dumps(data, indent=2)}')
        
        if not data:
            log.debug('OEmbedParse: No data to format')
            return None

        parts = []
        if data.get('title'):
            parts.append(data['title'])
        if data.get('author_name'):
            parts.append(f"by {data['author_name']}")
        if data.get('provider_name'):
            parts.append(f"via {data['provider_name']}")

        formatted = ' | '.join(parts) if parts else None
        log.debug(f'OEmbedParse: Formatted response: {formatted}')
        return formatted

    def doPrivmsg(self, irc, msg):
        """Listen for messages containing URLs and parse oEmbed data if URL matches a configured domain."""
        channel = msg.args[0]
        if not channel.startswith('#'):
            return
        
        if not self.registryValue('enabled', channel):
            log.debug(f'OEmbedParse: Plugin disabled in channel {channel}')
            return

        text = msg.args[1]
        log.debug(f'OEmbedParse: Processing message: {text}')
        
        urls = self._extract_urls(text)
        
        for url in urls:
            domain = self._get_domain(url)
            if not self._is_monitored_domain(domain):
                log.debug(f'OEmbedParse: Skipping non-monitored domain {domain}')
                continue

            try:
                log.debug(f'OEmbedParse: Processing URL {url}')
                oembed_data = self._fetch_oembed_data(url)
                
                if oembed_data:
                    response = self._format_oembed_response(oembed_data)
                    if response:
                        log.debug(f'OEmbedParse: Sending response: {response}')
                        irc.reply(response, prefixNick=False)
                        continue

                # Fallback to title if enabled
                if self.registryValue('enableTitleFallback'):
                    log.debug('OEmbedParse: Attempting title fallback')
                    title = self._get_page_title(url)
                    if title:
                        log.debug(f'OEmbedParse: Sending title fallback: {title}')
                        irc.reply(f'Title: {title}', prefixNick=False)
                    else:
                        log.debug('OEmbedParse: No title found in fallback')

            except Exception as e:
                log.error(f'OEmbedParse: Error processing URL {url}: {str(e)}')

Class = OEmbedParse
