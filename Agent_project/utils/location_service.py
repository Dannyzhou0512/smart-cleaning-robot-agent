import os
import requests

from Agent_project.utils.logger_handler import logger


def _to_text(value) -> str:
    """兼容高德返回的空字符串、列表、None 等情况。"""
    if isinstance(value, str):
        return value.strip()
    return ""


def reverse_geocode_by_amap(longitude: float, latitude: float) -> dict:
    """
    根据经纬度调用高德逆地理编码接口，返回省、市、区县、街道和格式化地址。
    注意：高德 location 参数格式是 经度,纬度。
    """
    amap_key = os.getenv("AMAP_WEB_KEY")

    if not amap_key:
        logger.warning("未检测到 AMAP_WEB_KEY 环境变量，无法进行逆地理编码")
        return {
            "success": False,
            "province": "",
            "city": "",
            "district": "",
            "township": "",
            "formatted_address": "",
            "message": "未检测到 AMAP_WEB_KEY 环境变量",
        }

    url = "https://restapi.amap.com/v3/geocode/regeo"

    try:
        response = requests.get(
            url,
            params={
                "key": amap_key,
                "location": f"{longitude},{latitude}",
                "output": "json",
                "extensions": "base",
                "radius": 1000,
            },
            timeout=5,
        )

        data = response.json()
        logger.info(f"高德逆地理编码原始返回: {data}")

        if data.get("status") != "1":
            return {
                "success": False,
                "province": "",
                "city": "",
                "district": "",
                "township": "",
                "formatted_address": "",
                "message": f"高德逆地理编码失败: {data}",
            }

        regeocode = data.get("regeocode", {})
        address_component = regeocode.get("addressComponent", {})

        province = _to_text(address_component.get("province"))
        city = _to_text(address_component.get("city"))
        district = _to_text(address_component.get("district"))
        township = _to_text(address_component.get("township"))
        formatted_address = _to_text(regeocode.get("formatted_address"))

        adcode = _to_text(address_component.get("adcode"))

        # 直辖市场景下 city 可能为空或 []，用 province 兜底
        if not city:
            city = province

        return {
            "success": True,
            "province": province,
            "city": city,
            "district": district,
            "township": township,
            "formatted_address": formatted_address,
            "message": "ok",
            "adcode": adcode,
        }

    except Exception as e:
        logger.error(f"调用高德逆地理编码接口异常: {e}")
        return {
            "success": False,
            "province": "",
            "city": "",
            "district": "",
            "township": "",
            "formatted_address": "",
            "message": str(e),
        }


def format_location_text(location_info: dict) -> str:
    """把定位结果整理成适合传给 Agent 的字符串。"""
    if not location_info or not location_info.get("success"):
        return ""

    province = location_info.get("province", "")
    city = location_info.get("city", "")
    district = location_info.get("district", "")
    township = location_info.get("township", "")
    address = location_info.get("formatted_address", "")

    parts = [p for p in [province, city, district, township] if p]

    if address:
        return f"用户当前位置：{''.join(parts)}，详细地址：{address}"

    return f"用户当前位置：{''.join(parts)}"