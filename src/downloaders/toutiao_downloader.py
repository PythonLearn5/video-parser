import json
import random
import base64
import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from src.downloaders.base_downloader import BaseDownloader
from configs.general_constants import USER_AGENT_PC
from configs.logging_config import logger


class ToutiaoDownloader(BaseDownloader):
    def __init__(self, real_url):
        super().__init__(real_url)
        self.headers = {
            "content-type": "application/json; charset=UTF-8",
            "User-Agent": random.choice(USER_AGENT_PC),
            "referer": "https://www.toutiao.com/"
        }
        self.html_content = self.fetch_html_content() or ""
        self._api_payload = self._fetch_info_api_data()

    @staticmethod
    def _normalize_url(url):
        if not url:
            return None
        url = str(url).replace("\\/", "/").strip()
        if url.startswith("//"):
            return "https:" + url
        return url

    def _meta_content(self, soup, selectors):
        for attrs in selectors:
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                return str(tag.get("content")).replace("\\/", "/")
        return None

    def _jsonld_video_data(self, soup):
        script_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
        for script in script_tags:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue

            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                type_name = item.get("@type", "")
                if isinstance(type_name, list):
                    is_video = "VideoObject" in type_name
                else:
                    is_video = type_name == "VideoObject"
                if is_video:
                    return item
        return {}

    @staticmethod
    def _extract_group_id(url):
        parsed = urlparse(url)
        query_group_id = parse_qs(parsed.query).get("group_id", [None])[0]
        if query_group_id:
            return query_group_id
        path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
        if path_segments:
            return path_segments[-1]
        return None

    def _fetch_info_api_data(self):
        try:
            group_id = self._extract_group_id(self.real_url)
            if not group_id:
                return {}
            info_url = f"https://m.toutiao.com/i{group_id}/info/"
            resp = requests.get(info_url, headers=self.headers, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                return {}
            return data.get("data") or {}
        except Exception as e:
            logger.warning(f"Failed to fetch Toutiao info API data: {e}")
            return {}

    def _api_play_info(self):
        api_data = self._api_payload or {}
        token_v2 = api_data.get("play_auth_token_v2")
        if not token_v2:
            return {}
        try:
            decoded = base64.b64decode(token_v2).decode("utf-8")
            token_data = json.loads(decoded)
            query_string = token_data.get("GetPlayInfoToken")
            if not query_string:
                return {}
            play_info_url = f"https://vod.bytedanceapi.com/?{query_string}"
            resp = requests.get(play_info_url, headers=self.headers, timeout=8)
            resp.raise_for_status()
            payload = resp.json()
            return (((payload or {}).get("Result") or {}).get("Data")) or {}
        except Exception as e:
            logger.warning(f"Failed to fetch Toutiao play info: {e}")
            return {}

    def get_real_video_url(self):
        try:
            # 反爬页面场景下，优先走官方移动端详情 + VOD 播放信息接口。
            play_info = self._api_play_info()
            play_list = play_info.get("PlayInfoList") or []
            if play_list:
                best_item = max(play_list, key=lambda item: item.get("Bitrate") or 0)
                main_url = best_item.get("MainPlayUrl") or best_item.get("BackupPlayUrl")
                if main_url:
                    return self._normalize_url(main_url)

            if not self.html_content:
                return None
            soup = BeautifulSoup(self.html_content, "html.parser")
            # 优先直接读取 video 标签（头条页面常见这种结构）
            video_tag = soup.find("video", src=True)
            if video_tag and video_tag.get("src"):
                return self._normalize_url(video_tag.get("src"))

            video_url = self._meta_content(soup, [
                {"property": "og:video"},
                {"property": "og:video:url"},
                {"name": "twitter:player:stream"},
                {"itemprop": "contentUrl"}
            ])
            if video_url:
                return self._normalize_url(video_url)
            jsonld_data = self._jsonld_video_data(soup)
            return self._normalize_url(
                jsonld_data.get("contentUrl") or jsonld_data.get("embedUrl") or None
            )
        except Exception as e:
            logger.warning(f"Failed to parse Toutiao video URL: {e}")
            return None

    def get_title_content(self):
        try:
            if self._api_payload and self._api_payload.get("title"):
                return str(self._api_payload.get("title"))

            if not self.html_content:
                return None
            soup = BeautifulSoup(self.html_content, "html.parser")
            title = self._meta_content(soup, [
                {"property": "og:title"},
                {"name": "twitter:title"}
            ])
            if title:
                return title

            jsonld_data = self._jsonld_video_data(soup)
            if jsonld_data.get("name"):
                return str(jsonld_data["name"])

            if soup.title and soup.title.string:
                return soup.title.string.strip()
            return None
        except Exception as e:
            logger.warning(f"Failed to parse Toutiao title: {e}")
            return None

    def get_cover_photo_url(self):
        try:
            if self._api_payload:
                cover = self._api_payload.get("poster_url")
                if cover:
                    return self._normalize_url(cover)

            if not self.html_content:
                return None
            soup = BeautifulSoup(self.html_content, "html.parser")
            cover_url = self._meta_content(soup, [
                {"property": "og:image"},
                {"name": "twitter:image"},
                {"itemprop": "thumbnailUrl"}
            ])
            if cover_url:
                return self._normalize_url(cover_url)
            jsonld_data = self._jsonld_video_data(soup)
            thumbnail = jsonld_data.get("thumbnailUrl")
            if isinstance(thumbnail, list) and thumbnail:
                return self._normalize_url(thumbnail[0])
            if isinstance(thumbnail, str):
                return self._normalize_url(thumbnail)
            return None
        except Exception as e:
            logger.warning(f"Failed to parse Toutiao cover URL: {e}")
            return None
