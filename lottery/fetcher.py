"""Fetch historical 双色球 data from online sources."""

import re
import time
import logging
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .models import Draw
from .storage import load_draws, save_draws, is_cache_stale, merge_draws

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _scrape_500com(start: str, end: str | None) -> list[Draw]:
    """Scrape historical data from datachart.500.com."""
    if end is None:
        now = datetime.now()
        year_suffix = str(now.year)[2:]
        week_num = now.isocalendar()[1]
        # Estimate latest issue based on current date
        # SSQ: ~3 draws/week, ~150/year. Current issue approx year*1000 + draw_number
        end = f"{year_suffix}{week_num * 3:03d}"

    url = f"https://datachart.500.com/ssq/history/newinc/history.php?start={start}&end={end}"
    logger.info("Fetching from 500.com: %s", url)

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    resp.encoding = "gb2312"

    soup = BeautifulSoup(resp.text, "lxml")
    # Find the main data table - it's the one with id="tdata"
    table = soup.find("table", id="tdata")
    if table is None:
        table = soup.find("table", class_="t_data")
    if table is None:
        # fallback: find the largest table
        tables = soup.find_all("table")
        if tables:
            table = max(tables, key=lambda t: len(t.find_all("tr")))

    if table is None:
        raise RuntimeError("Cannot find data table on 500.com page")

    draws = []
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 8:
            continue
        try:
            issue = cells[0].get_text(strip=True)
            # Validate issue format (e.g., "2024145")
            if not re.match(r"^\d{5,7}$", issue):
                continue

            reds = []
            for i in range(1, 7):
                reds.append(int(cells[i].get_text(strip=True)))

            blue = int(cells[7].get_text(strip=True))

            if not (all(1 <= r <= 33 for r in reds) and 1 <= blue <= 16):
                continue
            if len(set(reds)) != 6:
                continue

            # Date may be in cell[15] or similar, try to find it
            date_str = ""
            for c in cells[8:]:
                t = c.get_text(strip=True)
                if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
                    date_str = t
                    break
            if not date_str:
                date_str = "unknown"

            draws.append(Draw(issue=issue, date=date_str, reds=tuple(sorted(reds)), blue=blue))
        except (ValueError, IndexError):
            continue

    logger.info("Fetched %d draws from 500.com", len(draws))
    if not draws:
        raise RuntimeError("No valid draws parsed from 500.com")
    return draws


def _scrape_cwlgovcn(page_size: int = 100) -> list[Draw]:
    """Fetch from official cwl.gov.cn API as fallback."""
    draws = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": "https://www.cwl.gov.cn/",
        "Accept": "application/json",
    })

    for page in range(0, 30):
        url = (
            "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
            f"?name=ssq&pageNo={page + 1}&pageSize={page_size}&systemType=PC"
        )
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", [])
            if not items:
                break
            for item in items:
                code = item.get("code", "")
                red_str = item.get("red", "")
                blue_str = item.get("blue", "")
                date_str = item.get("date", "unknown")
                if not red_str or not blue_str:
                    continue
                reds = tuple(sorted(int(x) for x in red_str.split(",")))
                if len(reds) != 6:
                    continue
                blue = int(blue_str)
                draws.append(Draw(issue=code, date=date_str, reds=reds, blue=blue))
            time.sleep(0.3)
        except Exception as exc:
            logger.warning("cwl.gov.cn page %s fetch failed: %s", page + 1, exc)
            break

    logger.info("Fetched %d draws from cwl.gov.cn", len(draws))
    return draws


def fetch_draws(
    start_issue: str = "03001",
    end_issue: str | None = None,
    use_cache: bool = True,
    force: bool = False,
) -> list[Draw]:
    """Main entry point: fetch draws, using cache when available.

    Args:
        start_issue: Starting issue number (e.g., "03001" for 2003 issue 1)
        end_issue: Ending issue number, None for latest
        use_cache: Whether to use local cache
        force: Force re-fetch even if cache is fresh
    """
    cache_path = None
    if use_cache and not force:
        from .storage import get_cache_path
        cache_path = get_cache_path()
        if not force and not is_cache_stale(cache_path):
            cached = load_draws(cache_path)
            if cached:
                logger.info("Using cached data: %d draws", len(cached))
                return cached

    cached_draws = load_draws(cache_path) if cache_path else []

    draws = []
    fetch_error = None

    try:
        draws = _scrape_500com(start_issue, end_issue)
    except Exception as e:
        fetch_error = e
        logger.warning("500.com fetch failed: %s", e)
        try:
            draws = _scrape_cwlgovcn()
        except Exception as e2:
            logger.warning("cwl.gov.cn fetch also failed: %s", e2)

    if not draws:
        if cached_draws:
            logger.info("Falling back to cached data (%d draws)", len(cached_draws))
            return cached_draws
        raise RuntimeError(
            f"Failed to fetch data from all sources. Last error: {fetch_error}"
        )

    if cached_draws:
        draws = merge_draws(cached_draws, draws)

    if cache_path:
        save_draws(draws, cache_path)

    return draws
