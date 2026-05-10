from langchain_core.tools import tool
from rag.query_rewrite_service import QueryRewriteService
from rag.rag_service import RagSummarizeService
import random
from Agent_project.utils.config_handler import agents_config
from Agent_project.utils.path_tool import get_abs_path
import os
from Agent_project.utils.logger_handler import logger
import requests
rag = RagSummarizeService()
query_rewriter = QueryRewriteService()
user_ids = ["1234567890", "9876543210", "1111111111", "2222222222", "3333333333"]
month_arr = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
extra_data = {}
user_location_context = {}
user_profile_context = {}
conversation_memory_context = []
last_query_rewrite = {}


def clear_last_rag_sources() -> None:
    rag.clear_last_sources()


def get_last_rag_sources() -> list[dict]:
    return rag.get_last_sources()


def set_conversation_memory_context(messages: list[dict]) -> None:
    global conversation_memory_context
    conversation_memory_context = messages or []


def clear_last_query_rewrite() -> None:
    global last_query_rewrite
    last_query_rewrite = {}


def get_last_query_rewrite() -> dict:
    return last_query_rewrite


def set_user_location_context(location_info: dict) -> None:
    """由 Streamlit 前端写入当前用户定位信息，供 Agent 工具读取。"""
    global user_location_context
    user_location_context = location_info or {}


def set_user_profile_context(profile_info: dict) -> None:
    """由 Streamlit 前端写入当前用户配置，供 Agent 工具读取。"""
    global user_profile_context
    user_profile_context = profile_info or {}


def get_user_location_context_text() -> str:
    """把当前定位上下文转换为字符串。"""
    if not user_location_context:
        return ""

    province = user_location_context.get("province", "")
    city = user_location_context.get("city", "")
    district = user_location_context.get("district", "")
    township = user_location_context.get("township", "")
    address = user_location_context.get("formatted_address", "")

    parts = [p for p in [province, city, district, township] if p]

    if address:
        return f"{''.join(parts)}，详细地址：{address}"

    return "".join(parts)

@tool(description="从向量存储中检索参考资料并生成回答，参考来源由前端单独展示")
def rag_summarize(query: str) -> str:
    global last_query_rewrite

    rewritten_query = query_rewriter.rewrite(query, conversation_memory_context)
    last_query_rewrite = {
        "original_query": query,
        "rewritten_query": rewritten_query,
    }

    logger.info(f"[RAG查询改写]原始query: {query}")
    logger.info(f"[RAG查询改写]改写query: {rewritten_query}")

    return rag.rag_summarize(rewritten_query)

def query_amap_weather_by_adcode(adcode: str) -> dict:
    """根据高德 adcode 查询实时天气。"""
    amap_key = os.getenv("AMAP_WEB_KEY")

    if not amap_key:
        logger.warning("未检测到 AMAP_WEB_KEY 环境变量，无法查询天气")
        return {
            "success": False,
            "message": "未检测到 AMAP_WEB_KEY 环境变量",
        }

    if not adcode:
        return {
            "success": False,
            "message": "缺少 adcode，无法查询天气",
        }

    url = "https://restapi.amap.com/v3/weather/weatherInfo"

    try:
        response = requests.get(
            url,
            params={
                "key": amap_key,
                "city": adcode,
                "extensions": "base",
                "output": "json",
            },
            timeout=5,
        )

        data = response.json()
        logger.info(f"高德天气原始返回: {data}")

        if data.get("status") != "1":
            return {
                "success": False,
                "message": f"高德天气查询失败: {data}",
            }

        lives = data.get("lives", [])

        if not lives:
            return {
                "success": False,
                "message": f"高德天气未返回 lives 数据: {data}",
            }

        live = lives[0]

        return {
            "success": True,
            "province": live.get("province", ""),
            "city": live.get("city", ""),
            "adcode": live.get("adcode", adcode),
            "weather": live.get("weather", ""),
            "temperature": live.get("temperature", ""),
            "winddirection": live.get("winddirection", ""),
            "windpower": live.get("windpower", ""),
            "humidity": live.get("humidity", ""),
            "reporttime": live.get("reporttime", ""),
            "message": "ok",
        }

    except Exception as e:
        logger.error(f"调用高德天气接口异常: {e}")
        return {
            "success": False,
            "message": str(e),
        }

@tool(description="根据城市编码或区域编码查询实时天气，以字符串形式返回")
def get_weather(city: str) -> str:
    """根据高德 adcode 或城市编码查询实时天气。"""
    result = query_amap_weather_by_adcode(city)

    if not result.get("success"):
        logger.warning(f"天气查询失败，使用模拟天气兜底: {result.get('message')}")
        return f"城市{city}的天气暂时查询失败，默认按晴天、气温26摄氏度、空气湿度50%处理。"

    return (
        f"{result.get('province')}{result.get('city')}当前天气："
        f"{result.get('weather')}，"
        f"气温{result.get('temperature')}摄氏度，"
        f"空气湿度{result.get('humidity')}%，"
        f"{result.get('winddirection')}风{result.get('windpower')}级，"
        f"发布时间：{result.get('reporttime')}。"
    )

@tool(description="获取用户当前位置的实时天气，优先使用浏览器定位得到的adcode；如果没有adcode，则返回天气查询失败提示")
def get_current_location_weather() -> str:
    """根据当前用户定位上下文中的 adcode 查询实时天气。"""
    if not user_location_context:
        return "当前还没有获取到用户定位信息，无法查询当前位置天气。"

    adcode = user_location_context.get("adcode", "")
    district = user_location_context.get("district", "")
    city = user_location_context.get("city", "")
    province = user_location_context.get("province", "")

    if not adcode:
        return f"已获取当前位置为{province}{city}{district}，但缺少adcode，暂时无法查询实时天气。"

    result = query_amap_weather_by_adcode(adcode)

    if not result.get("success"):
        return f"当前位置{province}{city}{district}天气查询失败：{result.get('message')}"

    return (
        f"当前位置{province}{city}{district}的实时天气为："
        f"{result.get('weather')}，"
        f"气温{result.get('temperature')}摄氏度，"
        f"空气湿度{result.get('humidity')}%，"
        f"{result.get('winddirection')}风{result.get('windpower')}级，"
        f"发布时间：{result.get('reporttime')}。"
    )

@tool(description="获取用户当前位置，优先返回浏览器定位得到的区县级地址；如果没有浏览器定位，则使用高德IP定位返回城市")
def get_user_location() -> str:
    """获取用户当前位置，优先使用浏览器经纬度逆地理编码结果，否则退回到高德 IP 定位。"""

    # 1. 优先使用前端浏览器定位结果
    context_text = get_user_location_context_text()
    if context_text:
        return context_text

    # 2. 没有浏览器定位时，使用高德 IP 定位兜底
    amap_key = os.getenv("AMAP_WEB_KEY")

    if not amap_key:
        logger.warning("未检测到 AMAP_WEB_KEY 环境变量，使用默认城市：北京")
        return "北京"

    url = "https://restapi.amap.com/v3/ip"

    try:
        response = requests.get(
            url,
            params={
                "key": amap_key,
                "output": "json",
            },
            timeout=5,
        )

        data = response.json()
        logger.info(f"高德IP定位原始返回: {data}")

        if data.get("status") != "1":
            logger.warning(f"高德IP定位失败: {data}")
            return "北京"

        city = data.get("city")
        province = data.get("province")

        if isinstance(city, str) and city.strip():
            return city.strip()

        if isinstance(province, str) and province.strip():
            return province.strip()

        logger.warning(f"高德IP定位未返回有效城市: {data}")
        return "北京"

    except Exception as e:
        logger.error(f"调用高德IP定位接口异常: {e}")
        return "北京"

@tool(description="获取用户的ID，以纯字符串形式返回")
def get_user_id() -> str:
    configured_user_id = user_profile_context.get("user_id", "")
    if configured_user_id:
        return configured_user_id

    return random.choice(user_ids)


@tool(description="获取当前月份，以纯字符形式返回")
def get_current_month() -> str:
    return random.choice(month_arr)


def generate_external_data():
    """
    {
    "user_id": "1234567890",
    "user_location": "北京",
    "current_month": "January"
    }
    :return:
    """
    if not extra_data:
        extra_data_path = get_abs_path(agents_config["extra_data_path"])

        if not os.path.exists(extra_data_path):
            raise FileNotFoundError(f"外部文件{extra_data_path}不存在")

        with open(extra_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(',')

                user_id: str = arr[0].replace('"', "")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")

                if user_id not in extra_data:
                    extra_data[user_id] = {}

                extra_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "消耗品": consumables,
                    "比较": comparison
                }


@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()

    try:
        return extra_data[user_id][month]
    except KeyError:
        logger.warning(f"{fetch_external_data}未能检索到用户：{user_id}在{month}的使用记录数据")
        return ""


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"


if __name__ == '__main__':
    print(fetch_external_data("1005", "2025-06"))
