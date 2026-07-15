"""HTTP collection engine driven by persisted RequestHeaders and parser rules."""

import json
import re
import ssl
from html import unescape
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


class CollectorError(RuntimeError):
    """A source request or parser failed in a user-visible way."""


def build_url(source, keyword):
    try:
        params = json.loads(source.get("fixed_params_json") or "{}")
    except json.JSONDecodeError as exc:
        raise CollectorError("固定参数不是有效 JSON") from exc
    params[source.get("keyword_param") or "word"] = keyword
    separator = "&" if "?" in source["base_url"] else "?"
    return source["base_url"] + separator + urlencode(params, doseq=True)


def _clean_text(value):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _parse_meta(text):
    text = _clean_text(text)
    if not text:
        return "", ""
    parts = re.split(r"\s{2,}|\s+-\s+|\s+", text, maxsplit=1)
    publisher = parts[0]
    published_at = parts[1] if len(parts) > 1 else ""
    return publisher, published_at


def _select_text(node, selector):
    selected = node.select_one(selector) if selector else None
    return _clean_text(selected.get_text(" ", strip=True)) if selected else ""


def parse_html(source, html, request_url, keyword):
    lowered = html.lower()
    if "百度安全验证" in html or "安全验证" in html or "mkdjump" in lowered:
        raise CollectorError("百度返回安全验证页，当前网络出口触发了反爬校验")
    try:
        rules = json.loads(source.get("parser_rules_json") or "{}")
    except json.JSONDecodeError as exc:
        raise CollectorError("解析规则不是有效 JSON") from exc
    soup = BeautifulSoup(html, "html.parser")
    item_selector = rules.get("item") or "article"
    nodes = soup.select(item_selector)
    results = []
    seen = set()
    for node in nodes:
        title_node = node.select_one(rules.get("title") or "a")
        if not title_node:
            continue
        title = _clean_text(title_node.get_text(" ", strip=True))
        href = urljoin(request_url, title_node.get("href") or "")
        if not title or not href or href in seen:
            continue
        seen.add(href)
        summary = _select_text(node, rules.get("summary", ""))
        meta = _select_text(node, rules.get("meta", ""))
        publisher, published_at = _parse_meta(meta)
        image_node = node.select_one(rules.get("image") or "img")
        image_url = ""
        if image_node:
            image_url = image_node.get("src") or image_node.get("data-src") or ""
            image_url = urljoin(request_url, image_url)
        results.append({
            "source_id": source["id"],
            "source_name": source["name"],
            "keyword": keyword,
            "title": title,
            "url": href,
            "summary": summary,
            "image_url": image_url,
            "publisher": publisher,
            "published_at": published_at,
        })
    if not results:
        title = _clean_text(soup.title.get_text()) if soup.title else ""
        suffix = f"（页面标题：{title}）" if title else ""
        raise CollectorError(f"请求成功，但当前解析规则未匹配到数据{suffix}")
    return results


def collect_source(source, keyword, limit=12, timeout=18):
    if not source or not source.get("enabled"):
        raise CollectorError("瞭源不存在或已停用")
    if source.get("method", "GET").upper() != "GET":
        raise CollectorError("当前版本仅支持 GET 类型瞭源")
    try:
        headers = json.loads(source.get("headers_json") or "{}")
    except json.JSONDecodeError as exc:
        raise CollectorError("RequestHeaders 不是有效 JSON") from exc
    request_url = build_url(source, keyword)
    request = Request(request_url, headers=headers, method="GET")
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read(4 * 1024 * 1024)
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                html = raw.decode(charset, errors="replace")
            except LookupError:
                html = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise CollectorError(f"请求失败：{exc}") from exc
    return parse_html(source, html, request_url, keyword)[:limit]
