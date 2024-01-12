"""原版没有这一段，从pro复制过来的"""
import calendar
from datetime import datetime
from datetime import timedelta
MAX_LENGTH = 1024  #NOTION 2000个字符限制https://developers.notion.com/reference/request-limits


def get_heading(level, content):
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:MAX_LENGTH],
                    },
                }
            ],
            "color": "default",
            "is_toggleable": False,
        },
    }


def get_table_of_contents():
    """获取目录"""
    return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}


def get_title(content):
    return {"title": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_rich_text(content):
    return {"rich_text": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_url(url):
    return {"url": url}


def get_file(url):
    return {"files": [{"type": "external", "name": "Cover", "external": {"url": url}}]}


def get_multi_select(names):
    return {"multi_select": [{"name": name} for name in names]}

"""原版get_date：
def get_date(start):
    return {
        "date": {
            "start": start,
            "time_zone": "Asia/Shanghai",
        }
    }"""
"""Pro版get_date"""
def get_date(start,end=None):
    return {
        "date": {
            "start": start,
            "end":end,
            "time_zone": "Asia/Shanghai",
        }
    }

def get_icon(url):
    return {"type": "external", "external": {"url": url}}


def get_select(name):
    return {"select": {"name": name}}


def get_number(number):
    return {"number": number}


def get_quote(content):
    return {
        "type": "quote",
        "quote": {
            "rich_text": [
                {
                    "type": "text",
                    # 原版代码："text": {"content": content},
                    "text": {"content": content[:MAX_LENGTH]},#pro复制过来的
                }
            ],
            "color": "default",
        },
    }


def get_callout(content, style, colorStyle, reviewId):
    # 根据不同的划线样式设置不同的emoji 直线type=0 背景颜色是1 波浪线是2
    #emoji = "📌"
    color = "brown_background"
    if style == 0:
        #emoji = "📍"
        color = "green_background"   
    elif style == 1:
        #color = "pink_background"
    # 如果reviewId不是空说明是笔记
    #if reviewId != None:
        #emoji = "📝"
        color == "gray_background"
    color = "default"
    # 根据划线颜色设置文字的颜色
    if colorStyle == 1:
        color = "default"
    elif colorStyle == 2:
        color = "default"
    elif colorStyle == 3:
        color = "default"
    elif colorStyle == 4:
        color = "default"
    elif colorStyle == 5:
        color = "default"
    return {
        "type": "callout",
        "callout": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:MAX_LENGTH],
                    },
                }
            ],
            "icon": {"emoji": default},
            "color": color,
        },
    }

def format_time(time):
    """将秒格式化为 xx时xx分格式"""
    result = ""
    hour = time // 3600
    if hour > 0:
        result += f"{hour}h,"
    minutes = time % 3600 // 60
    if minutes > 0:
        result += f"{minutes}min"
    return result

def format_date(date,format="%Y-%m-%d %H:%M:%S"):
    return date.strftime(format)
