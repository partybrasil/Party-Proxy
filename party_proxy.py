#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Party-Proxy: CLI for scraping and checking free public proxies
Supports HTTP, HTTPS, and SOCKS protocols
"""

import os
import re
import time
import logging
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "active_proxies.txt")
TIMEOUT = 5  # seconds for proxy check
MAX_WORKERS = 100  # concurrent threads for checking
CHECK_URL = "http://www.google.com"
CHECK_URL_HTTPS = "https://www.google.com"

# Proxy sources - free public proxy lists
PROXY_SOURCES = [
    # HTTP
    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt",
    "https://raw.githubusercontent.com/mzyui/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/elliottophellia/proxylist/master/results/http/global/http_checked.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/master/http.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/http_proxies.txt",
    "https://raw.githubusercontent.com/casa-ls/proxy-list/main/http",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",

    # HTTPS
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/master/https.txt",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/https.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",

    # SOCKS4
    "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks4.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks4.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks4_proxies.txt",
    "https://raw.githubusercontent.com/mzyui/proxy-list/main/socks4.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks4.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
    "https://raw.githubusercontent.com/elliottophellia/proxylist/master/results/socks4/global/socks4_checked.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/master/socks4.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/socks4_proxies.txt",
    "https://raw.githubusercontent.com/casa-ls/proxy-list/main/socks4",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",

    # SOCKS5
    "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks5.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks5_proxies.txt",
    "https://raw.githubusercontent.com/mzyui/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/elliottophellia/proxylist/master/results/socks5/global/socks5_checked.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/master/socks5.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/main/socks5_proxies.txt",
    "https://raw.githubusercontent.com/casa-ls/proxy-list/main/socks5",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",

    # MIX
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxies.txt",
    "https://raw.githubusercontent.com/mzyui/proxy-list/main/all.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/proxylist.txt",
    "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt",
    "https://raw.githubusercontent.com/gitrecon1455/fresh-proxy-list/main/proxylist.txt",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/unknown.txt",
]


class ProxyManager:
    """Manages proxy scraping, checking, and storage"""
    
    def __init__(self, output_dir=OUTPUT_DIR, output_file=OUTPUT_FILE):
        self.output_dir = output_dir
        self.output_file = output_file
        self.proxies: List[Dict[str, Any]] = []
        self.geoip_cache: Dict[str, Dict[str, Any]] = {}
        self.ensure_output_dir()

    def get_geoip(self, ip: str) -> Dict[str, Any]:
        """Fetch GeoIP info for an IP, with simple caching"""
        if ip in self.geoip_cache:
            return self.geoip_cache[ip]
        
        try:
            # Use ip-api.com (Limited to 45 per min, but we only call this for active proxies)
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    info = {
                        'country': data.get('country', 'Unknown'),
                        'countryCode': data.get('countryCode', '??'),
                        'region': data.get('regionName', ''),
                        'city': data.get('city', ''),
                        'isp': data.get('isp', '')
                    }
                    self.geoip_cache[ip] = info
                    return info
        except Exception as e:
            logger.debug(f"GeoIP error for {ip}: {e}")
        
        return {'country': 'Unknown', 'countryCode': '??'}

    def ensure_output_dir(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")

    def scrape_proxies(self, cancel_check=None, max_workers=MAX_WORKERS) -> Set[str]:
        """
        Scrape proxies from multiple sources
        Returns a set of unique proxies in format IP:PORT
        """
        proxies = set()
        logger.info("Starting proxy scraping from sources...")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_source(source):
            if cancel_check and cancel_check():
                return set()
            try:
                logger.info(f"Fetching from: {source}")
                response = requests.get(source, timeout=30)
                if response.status_code == 200:
                    found = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}', response.text)
                    logger.info(f"Found {len(found)} proxies from {source}")
                    return set(found)
                else:
                    logger.warning(f"Failed to fetch from {source}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching from {source}: {e}")
            return set()

        # Concurrent scraping across sources
        with ThreadPoolExecutor(max_workers=min(len(PROXY_SOURCES), max_workers)) as executor:
            try:
                future_to_source = {executor.submit(fetch_source, src): src for src in PROXY_SOURCES}
                for future in as_completed(future_to_source):
                    if cancel_check and cancel_check():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    proxies.update(future.result())
            except KeyboardInterrupt:
                logger.warning("\nScraping interrupted by user. Processing partial results...")
                executor.shutdown(wait=False, cancel_futures=True)
        
        logger.info(f"Total unique proxies scraped: {len(proxies)}")
        return proxies

    def detect_anonymity(self, proxy: str) -> str:
        """Detect anonymity level of a proxy"""
        try:
            proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            # Heuristic check using httpbin
            response = requests.get('http://httpbin.org/get', proxies=proxies, timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                headers = data.get('headers', {})
                
                # Check for proxy indicators
                via = headers.get('Via', '')
                forwarded = headers.get('X-Forwarded-For', '')
                
                if not via and not forwarded:
                    return "Elite"
                elif "proxy" in via.lower() or forwarded:
                    return "Anonymous"
                else:
                    return "Transparent"
        except:
            pass
        return "Unknown"

    def check_proxy(self, proxy: str) -> Dict[str, Any]:
        """
        Check if a proxy is working and gather metadata
        Returns dict with proxy info if working, None if not
        """
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Step 1: Connectivity and Latency
            start_time = time.time()
            response = requests.get(
                CHECK_URL,
                proxies=proxy_dict,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            latency = round((time.time() - start_time) * 1000, 2)  # ms
            
            if response.status_code == 200:
                # Step 2: Metadata (only for active)
                ip = proxy.split(':')[0]
                geo = self.get_geoip(ip)
                privacy = self.detect_anonymity(proxy)
                
                logger.debug(f"✓ {proxy} - Working ({geo['country']}, {privacy}, {latency}ms)")
                return {
                    'proxy': proxy,
                    'latency': latency,
                    'status': 'active',
                    'country': geo['country'],
                    'countryCode': geo['countryCode'],
                    'privacy': privacy,
                    'last_check': datetime.now().isoformat()
                }
            else:
                return None
        
        except Exception as e:
            # Catch all errors including urllib3.exceptions.HeaderParsingError
            # from malformed proxy responses
            logger.debug(f"✗ {proxy} - Failed: {type(e).__name__}")
            return None

    def check_proxies_concurrent(self, proxies_to_check: Set[str], callback=None) -> List[Dict[str, Any]]:
        """
        Check proxies concurrently using ThreadPoolExecutor
        Returns list of working proxy info dicts
        """
        logger.info(f"Starting concurrent proxy checking with {MAX_WORKERS} workers...")
        working_proxies = []
        total = len(proxies_to_check)
        checked = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            try:
                future_to_proxy = {executor.submit(self.check_proxy, proxy): proxy for proxy in proxies_to_check}
                
                for future in as_completed(future_to_proxy):
                    checked += 1
                    if checked % 100 == 0 or checked == total:
                        logger.info(f"Progress: {checked}/{total} proxies checked")
                    
                    try:
                        result = future.result()
                        if result:
                            working_proxies.append(result)
                    except Exception as e:
                        logger.debug(f"Error checking proxy: {e}")
                    
                    if callback:
                        callback(checked, total, result)
            except KeyboardInterrupt:
                logger.warning("\nCheck interrupted by user. Saving partial results...")
                executor.shutdown(wait=False, cancel_futures=True)
        
        logger.info(f"Found {len(working_proxies)} working proxies out of {total}")
        return working_proxies

    def save_proxies(self, working_proxies: List[Dict[str, Any]]):
        """Save working proxies to output file"""
        self.ensure_output_dir()
        
        # Sort proxies for consistent output
        working_proxies.sort(key=lambda x: x['proxy'])
        
        with open(self.output_file, 'w') as f:
            for item in working_proxies:
                f.write(f"{item['proxy']}\n")
        
        logger.info(f"Saved {len(working_proxies)} proxies to {self.output_file}")

    def load_cached_proxies(self) -> List[str]:
        """Load proxies from the output file if it exists"""
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []

def update_readme_timestamp():
    """Update the timestamp in README.md"""
    readme_path = "README.md"
    
    if not os.path.exists(readme_path):
        logger.warning("README.md not found, skipping timestamp update")
        return
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get current timestamp
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S / %d-%m-%Y")
        
        # Update timestamp line
        updated_content = re.sub(
            r'\*\*⏰ Última actualización:\*\* .*',
            f'**⏰ Última actualización:** {timestamp}',
            content
        )
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"Updated README.md timestamp to: {timestamp}")
    
    except Exception as e:
        logger.error(f"Error updating README.md: {e}")


def main():
    """Main execution flow for CLI"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Party-Proxy: Starting proxy scraping and checking")
    logger.info("=" * 60)
    
    manager = ProxyManager()
    
    try:
        raw_proxies = set()
        working_proxies = []
        
        # Step 1: Scrape proxies from sources
        raw_proxies = manager.scrape_proxies()
        
        if not raw_proxies:
            logger.error("No proxies found from sources. Exiting.")
            return
        
        # Step 2: Check proxies concurrently
        working_proxies = manager.check_proxies_concurrent(raw_proxies)
        
    except KeyboardInterrupt:
        logger.warning("\nExecution stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        raise
    finally:
        # Step 3 & 4: Save what we have and update timestamp
        if 'working_proxies' in locals() and working_proxies:
            manager.save_proxies(working_proxies)
            update_readme_timestamp()
        
        # Summary
        elapsed_time = round(time.time() - start_time, 2)
        logger.info("=" * 60)
        logger.info("Party-Proxy: Execution finished")
        if 'raw_proxies' in locals():
            logger.info(f"Total proxies scraped: {len(raw_proxies)}")
        if 'working_proxies' in locals():
            logger.info(f"Working proxies found: {len(working_proxies)}")
            if 'raw_proxies' in locals() and raw_proxies:
                logger.info(f"Success rate: {round(len(working_proxies)/len(raw_proxies)*100, 2)}%")
        logger.info(f"Total execution time: {elapsed_time} seconds")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
