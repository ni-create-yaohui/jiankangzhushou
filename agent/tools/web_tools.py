"""
网络工具模块 - 提供真实的网络数据获取能力
"""
import requests
from langchain_core.tools import tool
from project.logger_handler import logger


@tool(description="获取指定城市的实时天气信息，包括温度、湿度、风速等。参数city为城市名称（支持中文或英文）")
def get_weather(city: str) -> str:
    """使用 wttr.in 免费API获取真实天气信息"""
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        response = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.68.0"})

        if response.status_code != 200:
            return f"获取天气失败：HTTP {response.status_code}"

        data = response.json()
        current = data.get("current_condition", [{}])[0]
        weather_desc = current.get("lang_zh", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "未知"))
        temp = current.get("temp_C", "未知")
        feels_like = current.get("FeelsLikeC", "未知")
        humidity = current.get("humidity", "未知")
        wind_speed = current.get("windspeedKmph", "未知")
        wind_dir = current.get("winddir16Point", "未知")
        visibility = current.get("visibility", "未知")
        pressure = current.get("pressure", "未知")

        result = f"""城市：{city}
天气：{weather_desc}
当前温度：{temp}°C
体感温度：{feels_like}°C
湿度：{humidity}%
风速：{wind_speed} km/h
风向：{wind_dir}
能见度：{visibility} km
气压：{pressure} mb"""
        return result

    except requests.Timeout:
        return f"获取{city}天气超时，请稍后重试"
    except requests.RequestException as e:
        logger.error(f"[get_weather] 网络请求异常: {e}")
        return f"获取天气失败：网络错误"
    except Exception as e:
        logger.error(f"[get_weather] 解析异常: {e}")
        return f"获取天气失败：{str(e)}"


@tool(description="自动获取用户当前位置的天气信息。通过IP地址定位获取城市，然后获取该城市的天气数据。无需参数")
def get_weather_by_ip() -> str:
    """通过IP地址自动获取用户当前位置的天气信息"""
    try:
        location_url = "http://ip-api.com/json/?lang=zh-CN"
        location_response = requests.get(location_url, timeout=10)

        if location_response.status_code != 200:
            return f"获取位置失败：HTTP {location_response.status_code}"

        location_data = location_response.json()

        if location_data.get("status") != "success":
            return f"获取位置失败：{location_data.get('message', '未知错误')}"

        city = location_data.get("city", "北京")

        weather_url = f"https://wttr.in/{city}?format=j1&lang=zh"
        weather_response = requests.get(weather_url, timeout=10, headers={"User-Agent": "curl/7.68.0"})

        if weather_response.status_code != 200:
            return f"获取天气失败：HTTP {weather_response.status_code}"

        weather_data = weather_response.json()
        current = weather_data.get("current_condition", [{}])[0]
        weather_desc = current.get("lang_zh", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "未知"))
        temp = current.get("temp_C", "未知")
        feels_like = current.get("FeelsLikeC", "未知")
        humidity = current.get("humidity", "未知")
        wind_speed = current.get("windspeedKmph", "未知")
        wind_dir = current.get("winddir16Point", "未知")
        visibility = current.get("visibility", "未知")
        pressure = current.get("pressure", "未知")

        result = f"""位置信息（基于IP自动定位）
城市：{city}
省份：{location_data.get("regionName", "")}
国家：{location_data.get("country", "")}

天气信息
天气状况：{weather_desc}
当前温度：{temp}°C
体感温度：{feels_like}°C
湿度：{humidity}%
风速：{wind_speed} km/h
风向：{wind_dir}
能见度：{visibility} km
气压：{pressure} mb"""
        return result

    except requests.Timeout:
        return "获取天气超时，请稍后重试"
    except requests.RequestException as e:
        logger.error(f"[get_weather_by_ip] 网络请求异常: {e}")
        return "获取天气失败：网络错误"
    except Exception as e:
        logger.error(f"[get_weather_by_ip] 解析异常: {e}")
        return f"获取天气失败：{str(e)}"


@tool(description="通过网络搜索获取实时信息。参数query为搜索关键词，返回相关搜索结果摘要")
def web_search(query: str) -> str:
    """使用 DuckDuckGo 进行网络搜索"""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5))

        if not search_results:
            return f"未找到关于'{query}'的相关信息"

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


@tool(description="根据IP地址获取用户的地理位置信息，包括国家、省份、城市等。无需参数")
def get_user_location() -> str:
    """通过IP-API免费服务获取用户真实地理位置"""
    try:
        url = "http://ip-api.com/json/?lang=zh-CN"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return f"获取位置失败：HTTP {response.status_code}"

        data = response.json()

        if data.get("status") != "success":
            return f"获取位置失败：{data.get('message', '未知错误')}"

        country = data.get("country", "未知")
        region = data.get("regionName", "未知")
        city = data.get("city", "未知")
        isp = data.get("isp", "未知")
        ip = data.get("query", "未知")
        lat = data.get("lat", 0)
        lon = data.get("lon", 0)

        result = f"""当前位置信息：
国家/地区：{country}
省份：{region}
城市：{city}
IP地址：{ip}
网络服务商：{isp}
坐标：{lat}, {lon}"""
        return result

    except requests.Timeout:
        return "获取位置超时，请稍后重试"
    except requests.RequestException as e:
        logger.error(f"[get_user_location] 网络请求异常: {e}")
        return "获取位置失败：网络错误"
    except Exception as e:
        logger.error(f"[get_user_location] 解析异常: {e}")
        return f"获取位置失败：{str(e)}"


@tool(description="抓取指定网页的内容并返回文本摘要。参数url为网页地址")
def fetch_webpage(url: str) -> str:
    """抓取网页内容并提取正文"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, timeout=15, headers=headers)

        if response.status_code != 200:
            return f"抓取网页失败：HTTP {response.status_code}"

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

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
        logger.error(f"[fetch_webpage] 网络请求异常: {e}")
        return f"抓取网页失败：网络错误"
    except Exception as e:
        logger.error(f"[fetch_webpage] 解析异常: {e}")
        return f"抓取网页失败：{str(e)}"


@tool(description="获取当前真实的日期和时间，返回格式如：2025-01-15 14:30:00 星期三")
def get_current_datetime() -> str:
    """获取当前真实日期时间"""
    from datetime import datetime
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()
    weekday = weekdays[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {weekday}"
