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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set, Dict, Any
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
MAX_WORKERS = 999  # concurrent threads for checking
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


def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")


def scrape_proxies() -> Set[str]:
    """
    Scrape proxies from multiple sources
    Returns a set of unique proxies in format IP:PORT
    """
    proxies = set()
    logger.info("Starting proxy scraping from sources...")
    
    for source in PROXY_SOURCES:
        try:
            logger.info(f"Fetching from: {source}")
            response = requests.get(source, timeout=30)
            if response.status_code == 200:
                content = response.text
                # Extract IP:PORT patterns
                found = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}', content)
                proxies.update(found)
                logger.info(f"Found {len(found)} proxies from this source")
            else:
                logger.warning(f"Failed to fetch from {source}: Status {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
            continue
    
    logger.info(f"Total unique proxies scraped: {len(proxies)}")
    return proxies


def check_proxy(proxy: str) -> Dict[str, Any]:
    """
    Check if a proxy is working
    Returns dict with proxy info if working, None if not
    """
    try:
        proxy_dict = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        
        # Try HTTP first
        start_time = time.time()
        response = requests.get(
            CHECK_URL,
            proxies=proxy_dict,
            timeout=TIMEOUT,
            allow_redirects=True
        )
        latency = round((time.time() - start_time) * 1000, 2)  # ms
        
        if response.status_code == 200:
            logger.debug(f"✓ {proxy} - Working (latency: {latency}ms)")
            return {
                'proxy': proxy,
                'latency': latency,
                'status': 'active'
            }
        else:
            logger.debug(f"✗ {proxy} - Status code: {response.status_code}")
            return None
            
    except Exception as e:
        logger.debug(f"✗ {proxy} - Failed: {str(e)[:50]}")
        return None


def check_proxies_concurrent(proxies: Set[str]) -> List[str]:
    """
    Check proxies concurrently using ThreadPoolExecutor
    Returns list of working proxies
    """
    logger.info(f"Starting concurrent proxy checking with {MAX_WORKERS} workers...")
    working_proxies = []
    total = len(proxies)
    checked = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_proxy = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
        
        for future in as_completed(future_to_proxy):
            checked += 1
            if checked % 100 == 0 or checked == total:
                logger.info(f"Progress: {checked}/{total} proxies checked")
            
            result = future.result()
            if result:
                working_proxies.append(result['proxy'])
    
    logger.info(f"Found {len(working_proxies)} working proxies out of {total}")
    return working_proxies


def save_proxies(proxies: List[str]):
    """Save working proxies to output file"""
    ensure_output_dir()
    
    # Sort proxies for consistent output
    proxies.sort()
    
    with open(OUTPUT_FILE, 'w') as f:
        for proxy in proxies:
            f.write(f"{proxy}\n")
    
    logger.info(f"Saved {len(proxies)} proxies to {OUTPUT_FILE}")


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
    """Main execution flow"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Party-Proxy: Starting proxy scraping and checking")
    logger.info("=" * 60)
    
    try:
        # Step 1: Scrape proxies from sources
        proxies = scrape_proxies()
        
        if not proxies:
            logger.error("No proxies found from sources. Exiting.")
            return
        
        # Step 2: Check proxies concurrently
        working_proxies = check_proxies_concurrent(proxies)
        
        if not working_proxies:
            logger.warning("No working proxies found. Creating empty output file.")
            working_proxies = []
        
        # Step 3: Save working proxies
        save_proxies(working_proxies)
        
        # Step 4: Update README timestamp
        update_readme_timestamp()
        
        # Summary
        elapsed_time = round(time.time() - start_time, 2)
        logger.info("=" * 60)
        logger.info("Party-Proxy: Execution completed successfully")
        logger.info(f"Total proxies scraped: {len(proxies)}")
        logger.info(f"Working proxies found: {len(working_proxies)}")
        logger.info(f"Success rate: {round(len(working_proxies)/len(proxies)*100, 2)}%")
        logger.info(f"Total execution time: {elapsed_time} seconds")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()
