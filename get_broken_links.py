import concurrent.futures
import logging
import socket
import urllib.error
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import pandas as pd
from bs4 import BeautifulSoup
import multiprocessing
import time

# Domains that are allowed to return 403s to prevent bot detection
ALLOWED_403_DOMAINS = ['sciencedirect.com', 'openai.com', 'doi.org', 'machinehack.com']
IGNORE_STRINGS_IN_URL = ["twitter", "kaggle.com", "anaconda.org/conda-forge"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webchecker-logger")


def add_headers(req):
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0",
    )
    req.add_header(
        "Accept",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    )
    req.add_header("Accept-Language", "en-US,en;q=0.5")


def get_all_links(url):
    # URLs to ignore
    links = set()
    if url.split(".")[-1] == "ipynb" or any(
        substring in url for substring in IGNORE_STRINGS_IN_URL
    ):
        return links
    try:
        req = Request(url)
        add_headers(req)
        response = urlopen(req, timeout=5)

        parsed_start_url = urlparse(start_url)
        domain = parsed_start_url.netloc  # this will be "auto.gluon.ai"
        stable_or_dev = parsed_start_url.path.split("/")[1]
        if response.code == 200 and domain + "/" + stable_or_dev in url:
            mybytes = response.fp.read()
            html = str(mybytes)
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a"):
                href = link.get("href")
                if href and not href.startswith("#"):  # Exclude anchor links
                    absolute_url = urljoin(url, href)
                    parsed_url = urlparse(absolute_url)
                    if parsed_url.scheme and parsed_url.netloc:  # Ensure valid URL
                        links.add(absolute_url)
                        parent_links[absolute_url] = url  # Store the parent link
            return links
    except (TimeoutError, socket.timeout):
        logger.error(f"Request timed out for {url}")
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        logger.error(f"Error while processing {url}: {e}")
        links.add(url)
    return links


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((TimeoutError, socket.timeout, urllib.error.URLError, urllib.error.HTTPError, socket.gaierror)),
    reraise=True
)
def check_link_status(link):
    logger.info(f"Testing URL: {link}")
    if link.split(".")[-1] == "ipynb" or any(
        substring in link for substring in IGNORE_STRINGS_IN_URL
    ):
        return link, 0
        
    try:
        if urlparse(link).scheme not in ['http', 'https']:
            return link, f"Invalid URL scheme: {urlparse(link).scheme}"
            
        req = Request(link)
        add_headers(req)
        
        # Add longer timeout and handle more error cases
        try:
            response = urlopen(req, timeout=20)
            return link, response.code
            
        except urllib.error.HTTPError as e:
            # Handle whitelisted domains
            if any(domain in link for domain in ALLOWED_403_DOMAINS):
                if e.code in (301, 302, 307, 308, 403):
                    return link, 200
            return link, e.code
            
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError) as e:
            # Handle connection errors
            error_msg = str(e)
            if "nodename nor servname provided" in error_msg:
                # DNS resolution error - likely valid URL but temporary DNS issue
                return link, 200
            elif "Connection reset by peer" in error_msg:
                # Connection reset - likely valid URL but server terminated connection
                return link, 200
            else:
                logger.error(f"Error while checking {link}: {e}")
                return link, str(e)
                
    except Exception as e:
        logger.error(f"Unexpected error while checking {link}: {e}")
        return link, str(e)


def main(start_url, filename):
    global parent_links  # Use a global variable to store the parent links
    all_links = set([start_url])
    crawled_links = set()
    broken_links = []
    max_workers = multiprocessing.cpu_count() * 2

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        parent_links = {
            start_url: start_url
        }  # Initialize the parent_links dictionary with the start_url
        while all_links - crawled_links:
            # Process links in batches to improve efficiency
            batch_links = list(all_links - crawled_links)[:max_workers]
            crawled_links |= set(batch_links)

            # Crawl each link and get new links
            links = {executor.submit(get_all_links, link): link for link in batch_links}

            for valid_sub_link in concurrent.futures.as_completed(links):
                new_links = valid_sub_link.result()
                all_links |= new_links - crawled_links

            # Check link status concurrently
            link_statuses = {
                executor.submit(check_link_status, link): link for link in batch_links
            }
            for link_status in concurrent.futures.as_completed(link_statuses):
                link, status_code = link_status.result()
                crawled_links.add(link)
                if isinstance(status_code, str):
                    if "HTTPSConnectionPool" in status_code:
                        continue
                    broken_links.append(
                        (
                            parent_links[link] + " ",
                            "".join(status_code.split(":")[:2]),
                            link,
                        )
                    )
                elif status_code >= 400 and status_code != 405:
                    broken_links.append((parent_links[link] + " ", status_code, link))

    # Convert broken links to a pandas DataFrame and display it
    df = pd.DataFrame(
        broken_links, columns=["Origin Webpage", "Status Code / Error", "URL"]
    )
    df.to_csv(f"Broken Links {filename}.csv", index=False)


if __name__ == "__main__":
    start_url = "https://auto.gluon.ai/stable/index.html"
    main(start_url, "Stable")
    start_url = "https://auto.gluon.ai/dev/index.html"
    main(start_url, "Dev")
