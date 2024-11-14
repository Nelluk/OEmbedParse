import re
import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import html
from supybot import callbacks, conf, ircmsgs, log, utils, world
from supybot.commands import *

# Maximum length for titles when doing fallback
MAX_TITLE_LENGTH = 200

class OEmbedParse(callbacks.Plugin):
    """
    A Limnoria plugin to parse oEmbed data for specified URL domains posted in an IRC channel.
    
    Basic usage:
    1. Enable in a specific channel:
        config channel #yourchannel plugins.OEmbedParse.enabled True
    
    2. Manage monitored domains using standard config commands:
        config plugins.OEmbedParse.domains  (list current domains)
        config plugins.OEmbedParse.domains add domain.com
        config plugins.OEmbedParse.domains remove domain.com
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

    def _parse_timestamp(self, timestamp_str):
        """Parse ISO timestamp into a more readable format."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception as e:
            log.error(f'OEmbedParse: Error parsing timestamp {timestamp_str}: {str(e)}')
            return timestamp_str

    def _parse_html_content(self, html_content):
        """Parse the HTML content from oEmbed data to extract meaningful text."""
        try:
            log.debug(f'OEmbedParse: Parsing HTML content:  {html_content}')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract the main post text
            post_text = ''
            p_tag = soup.find('p')
            if p_tag:
                post_text = p_tag.get_text().strip()
                log.debug(f'OEmbedParse: Extracted post text: {post_text}')
            
            # Extract timestamp
            timestamp_link = soup.find_all('a')[-1]  # Usually the last link contains the timestamp
            timestamp = ''
            if timestamp_link:
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)', timestamp_link['href'])
                if timestamp_match:
                    timestamp = self._parse_timestamp(timestamp_match.group(1))
                    log.debug(f'OEmbedParse: Extracted timestamp: {timestamp}')
            
            return {
                'text': post_text,
                'timestamp': timestamp
            }
        except Exception as e:
            log.error(f'OEmbedParse: Error parsing HTML content: {str(e)}')
            return None

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
                title = title.strip()
                original_length = len(title)
                
                if len(title) > MAX_TITLE_LENGTH:
                    title = title[:MAX_TITLE_LENGTH - 3] + '...'
                    log.debug(f'OEmbedParse: Title truncated from {original_length} to {MAX_TITLE_LENGTH} chars')
                
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

        try:
            # Parse the HTML content
            html_content = data.get('html', '')
            parsed_content = self._parse_html_content(html_content)
            
            if not parsed_content:
                log.debug('OEmbedParse: Failed to parse HTML content')
                return None

            # Build the response parts
            parts = []
            
            # Add the post text if available
            if parsed_content['text']:
                # Decode any HTML entities and normalize whitespace
                text = html.unescape(parsed_content['text'])
                text = ' '.join(text.split())  # Normalize whitespace
                parts.append(text)
            
            # Add the author
            if data.get('author_name'):
                parts.append(f"-- {data['author_name']}")
            
            # Add the timestamp
            if parsed_content['timestamp']:
                parts.append(f"({parsed_content['timestamp']})")

            formatted = ' '.join(parts) if parts else None
            log.debug(f'OEmbedParse: Formatted response: {formatted}')
            return formatted

        except Exception as e:
            log.error(f'OEmbedParse: Error formatting response: {str(e)}')
            return None

    def doPrivmsg(self, irc, msg):
        """Listen for messages containing URLs and parse oEmbed data if URL matches a configured domain."""
        channel = msg.args[0]
        if not channel.startswith('#'):
            return
        
        # Get channel-specific enabled status
        enabled = self.registryValue('enabled', channel)
        log.debug(f'OEmbedParse: Plugin enabled status for {channel}: {enabled}')
        
        if not enabled:
            log.debug(f'OEmbedParse: Plugin disabled in channel {channel}')
            return

        text = msg.args[1]
        log.debug(f'OEmbedParse: Processing message: {text}')
        
        urls = self._extract_urls(text)
        
        for url in urls:
            domain = self._get_domain(url)
            try:
                log.debug(f'OEmbedParse: Processing URL {url}')
                
                # Try oEmbed first for monitored domains
                if self._is_monitored_domain(domain):
                    oembed_data = self._fetch_oembed_data(url)
                    if oembed_data:
                        response = self._format_oembed_response(oembed_data)
                        if response:
                            log.debug(f'OEmbedParse: Sending response: {response}')
                            irc.reply(response, prefixNick=False)
                            continue

                # Fallback to title for all URLs
                title = self._get_page_title(url)
                if title:
                    log.debug(f'OEmbedParse: Sending title fallback: {title}')
                    irc.reply(f'Title: {title}', prefixNick=False)

            except Exception as e:
                log.error(f'OEmbedParse: Error processing URL {url}: {str(e)}')

Class = OEmbedParse
