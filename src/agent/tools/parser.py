"""
Parser Tool - HTML 解析工具

提供文本提取、表格提取、JSON-LD 提取等功能。
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
import json


class ParserTool:
    """HTML 解析工具"""

    def extract_text(self, html: str) -> str:
        """提取纯文本"""
        soup = BeautifulSoup(html, 'lxml')
        return soup.get_text(separator='\n', strip=True)

    def extract_table(self, html: str) -> List[Dict[str, Any]]:
        """提取表格数据"""
        soup = BeautifulSoup(html, 'lxml')
        tables = []

        for table_idx, table in enumerate(soup.find_all('table')):
            rows = []
            headers = []

            # 提取表头
            for th in table.find_all('th'):
                headers.append(th.get_text(strip=True))

            # 提取数据行
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    row_data = {}
                    if headers and len(cells) == len(headers):
                        for i, header in enumerate(headers):
                            row_data[header] = cells[i]
                    else:
                        row_data = {"cells": cells}
                    rows.append(row_data)

            if rows:
                tables.append({
                    "index": table_idx,
                    "headers": headers,
                    "rows": rows,
                })

        return tables

    def extract_json_ld(self, html: str) -> List[Dict]:
        """提取 JSON-LD 数据"""
        soup = BeautifulSoup(html, 'lxml')
        scripts = soup.find_all('script', type='application/ld+json')

        data = []
        for script in scripts:
            try:
                parsed = json.loads(script.string)
                data.append(parsed)
            except (json.JSONDecodeError, TypeError):
                continue

        return data

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """提取链接"""
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, 'lxml')
        links = []

        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            links.append(full_url)

        return links

    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """提取页面元数据"""
        soup = BeautifulSoup(html, 'lxml')
        metadata = {}

        # Title
        if soup.find('title'):
            metadata['title'] = soup.find('title').get_text(strip=True)

        # Meta description
        desc = soup.find('meta', attrs={'name': 'description'})
        if desc:
            metadata['description'] = desc.get('content', '')

        # Meta keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords:
            metadata['keywords'] = keywords.get('content', '')

        # OG tags
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata['og_title'] = og_title.get('content', '')

        return metadata
