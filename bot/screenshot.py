import aiohttp
import urllib.parse
from typing import Tuple
from logger import logger
import os

URLBOX_API_KEY = os.environ.get('URLBOX_API_KEY')


async def fetch_urlbox_screenshot(url: str,
                                width: int = 500,
                                height: int = 580,
                                scroll: str = "") -> Tuple[str, str]:
    """
    Fetch a screenshot URL and HTML data from URLBox API.

    Args:
        url: The URL to screenshot
        width: Viewport width (pixels)
        height: Viewport height (pixels)
        scroll: Scroll position as string. Can be:
               - Pixel value: "300px"
               - CSS selector: ".class-name" or "#element-id"
               - Percentage: "50%"

    Returns:
        Tuple[str, str]: (image_url, html_data)
    """
    if not url:
        raise ValueError("URL cannot be empty")
    logger.info(f"Starting screenshot fetch for URL: {url}")

    # Parse the URL first
    parsed_url = urllib.parse.urlparse(url)
    # Get the query parameters as a dictionary
    query_params = urllib.parse.parse_qs(parsed_url.query)
    # Rebuild query parameters with proper encoding
    encoded_query = urllib.parse.urlencode(query_params, doseq=True)
    # Rebuild the URL with encoded query
    encoded_url = urllib.parse.urlunparse(
        (parsed_url.scheme, parsed_url.netloc, parsed_url.path,
         parsed_url.params, encoded_query, parsed_url.fragment))
    logger.info(f"Encoded URL for URLBox request: {encoded_url}")

    # Build URLBox parameters
    params = {
        'url': encoded_url,
        'width': str(width),
        'height': str(height),
        'scroll_to': scroll,
        'block_ads': 'true',
        'save_html': 'true',
        'force': 'true',
        'response_type': 'json',
        'user_agent': 'random'
    }

    # Construct URLBox API URL
    base_url = f"https://api.urlbox.com/v1/{URLBOX_API_KEY}/png"
    query_string = urllib.parse.urlencode(params)
    urlbox_url = f"{base_url}?{query_string}"

    logger.info(
        f"Fetching URLBox screenshot with params: width={width}, height={height}, scroll_to={scroll}"
    )

    async with aiohttp.ClientSession() as session:
        try:
            # Fetch API response
            async with session.get(urlbox_url) as response:
                api_response_text = await response.text()
                if response.status != 200:
                    error_msg = f"URLBox API Error: Status {response.status}"
                    logger.error(
                        f"❌ {error_msg} - Response: {api_response_text[:500]}")
                    raise Exception(error_msg)

                # Parse JSON response
                try:
                    render_info = await response.json()
                    logger.info(f"URLBox API Response: {render_info}")
                except Exception as e:
                    error_msg = "Invalid JSON response from URLBox API"
                    logger.error(
                        f"❌ JSON parsing error: {str(e)} - Raw API Response: {api_response_text[:500]}"
                    )
                    raise Exception(error_msg)

                render_url = render_info.get("renderUrl")
                html_url = render_info.get("htmlUrl")

                if not render_url or not html_url:
                    error_msg = "Missing render URL or HTML URL in response"
                    logger.error(
                        f"❌ {error_msg} - API Response: {render_info}")
                    raise Exception(error_msg)

                logger.info(f"Got render URL: {render_url}")
                logger.info(f"Got HTML URL: {html_url}")

                # Fetch the HTML data with detailed error handling
                logger.info("Fetching HTML content...")
                try:
                    async with session.get(html_url) as html_response:
                        if html_response.status != 200:
                            error_msg = f"Failed to get HTML data: Status {html_response.status}"
                            response_text = await html_response.text()
                            logger.error(f"❌ HTML fetch failed: {error_msg}")
                            logger.error(f"Response content: {response_text[:500]}")
                            raise Exception(error_msg)

                        html_data = await html_response.text()
                        if not html_data:
                            raise ValueError("Empty HTML response received")

                        logger.info(f"Successfully fetched HTML data (length: {len(html_data)})")
                        return render_url, html_data

                except aiohttp.ClientError as ce:
                    error_msg = f"Network error while fetching HTML: {str(ce)}"
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error while fetching HTML: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"❌ Error in fetch_urlbox_screenshot: {str(e)}")
            raise