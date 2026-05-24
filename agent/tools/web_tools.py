"""
网络工具模块 - 提供天气、搜索、网页抓取等网络能力
"""
import re
import requests
from langchain_core.tools import tool
from project.logger_handler import logger


# ==================== 内部辅助函数 ====================

def _parse_wttr_response(data: dict) -> dict:
    """解析 wttr.in JSON 响应，返回天气字段 dict"""
    current = data.get("current_condition", [{}])[0]
    return {
        "weather_desc": current.get("lang_zh", [{}])[0].get(
            "value", current.get("weatherDesc", [{}])[0].get("value", "未知")
        ),
        "temp": current.get("temp_C", "未知"),
        "feels_like": current.get("FeelsLikeC", "未知"),
        "humidity": current.get("humidity", "未知"),
        "wind_speed": current.get("windspeedKmph", "未知"),
        "wind_dir": current.get("winddir16Point", "未知"),
        "visibility": current.get("visibility", "未知"),
        "pressure": current.get("pressure", "未知"),
    }


def _get_location_by_ip() -> dict:
    """通过 IP-API 获取位置信息，返回位置 dict 或抛异常"""
    response = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
    if response.status_code != 200:
        raise requests.RequestException(f"HTTP {response.status_code}")
    data = response.json()
    if data.get("status") != "success":
        raise ValueError(data.get("message", "未知错误"))
    return {
        "city": data.get("city", "未知"),
        "region": data.get("regionName", ""),
        "country": data.get("country", ""),
        "isp": data.get("isp", "未知"),
        "ip": data.get("query", "未知"),
        "lat": data.get("lat", 0),
        "lon": data.get("lon", 0),
    }


def _is_url(text: str) -> bool:
    """判断输入是否为 URL"""
    return bool(re.match(r"^https?://", text.strip(), re.IGNORECASE))


# ==================== 天气工具（合并原 get_weather + get_weather_by_ip + get_user_location） ====================

@tool(description=(
    "获取天气信息。提供城市名称返回指定城市天气；不提供城市则自动定位获取当前位置天气和城市信息。"
    "返回包含城市名称、温度、湿度、风速等信息的结构化字符串。"
))
def get_weather(city: str = "") -> str:
    """获取天气信息，city 为空时自动定位"""
    location_info = None

    if not city:
        try:
            location_info = _get_location_by_ip()
            city = location_info["city"]
        except Exception as e:
            logger.error(f"[get_weather] IP定位失败: {e}")
            return f"自动定位失败：{str(e)}，请提供城市名称"

    try:
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        response = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.68.0"})
        if response.status_code != 200:
            return f"获取天气失败：HTTP {response.status_code}"

        w = _parse_wttr_response(response.json())

        location_header = ""
        if location_info:
            location_header = f"位置信息（自动定位）\n城市：{city}\n省份：{location_info['region']}\n国家：{location_info['country']}\n\n天气信息\n"

        result = f"""{location_header}城市：{city}
天气：{w['weather_desc']}
当前温度：{w['temp']}°C
体感温度：{w['feels_like']}°C
湿度：{w['humidity']}%
风速：{w['wind_speed']} km/h
风向：{w['wind_dir']}
能见度：{w['visibility']} km
气压：{w['pressure']} mb"""
        return result

    except requests.Timeout:
        return f"获取{city}天气超时，请稍后重试"
    except requests.RequestException as e:
        logger.error(f"[get_weather] 网络请求异常: {e}")
        return "获取天气失败：网络错误"
    except Exception as e:
        logger.error(f"[get_weather] 解析异常: {e}")
        return f"获取天气失败：{str(e)}"


# ==================== 搜索工具（合并原 web_search + fetch_webpage） ====================

@tool(description=(
    "搜索网络信息或抓取网页内容。输入搜索关键词进行搜索，输入网址(以http://或https://开头)则抓取该网页内容。"
))
def web_search(query: str) -> str:
    """搜索网络信息或抓取网页内容，自动判断输入类型"""
    if _is_url(query):
        return _fetch_webpage(query)
    return _search_duckduckgo(query)


def _search_duckduckgo(query: str) -> str:
    """DuckDuckGo 搜索"""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5))

        if not search_results:
            return f"未找到关于'{query}'的相关信息"

        results = []
        for i, r in enumerate(search_results, 1):
            title = r.get("title", "无标题")
            href = r.get("href", "")
            body = r.get("body", "无描述")
            results.append(f"{i}. {title}\n   {body}\n   来源: {href}")

        return f"搜索'{query}'的结果：\n\n" + "\n\n".join(results)

    except ImportError:
        return "搜索功能不可用：请安装 duckduckgo-search 库"
    except Exception as e:
        logger.error(f"[web_search] 搜索异常: {e}")
        return f"搜索失败：{str(e)}"


def _fetch_webpage(url: str) -> str:
    """抓取网页内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, timeout=15, headers=headers)
        if response.status_code != 200:
            return f"抓取网页失败：HTTP {response.status_code}"

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines[:100])

        if len(content) > 2000:
            content = content[:2000] + "\n... (内容已截断)"

        return f"网页内容 ({url})：\n\n{content}"

    except ImportError:
        return "网页抓取功能不可用：请安装 beautifulsoup4 库"
    except requests.Timeout:
        return "抓取网页超时，请稍后重试"
    except requests.RequestException as e:
        logger.error(f"[_fetch_webpage] 网络请求异常: {e}")
        return "抓取网页失败：网络错误"
    except Exception as e:
        logger.error(f"[_fetch_webpage] 解析异常: {e}")
        return f"抓取网页失败：{str(e)}"


# ==================== 时间工具 ====================

@tool(description="获取当前真实的日期和时间，返回格式如：2025-01-15 14:30:00 星期三")
def get_current_datetime() -> str:
    """获取当前真实日期时间"""
    from datetime import datetime
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()
    weekday = weekdays[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {weekday}"
