import argparse
import json
import logging
import os
import re
import time
from notion_client import Client
import requests

from requests.utils import cookiejar_from_dict
from http.cookies import SimpleCookie
from datetime import datetime, timedelta #原本没有timedelta，新增timedelta
import hashlib

from utils import (
    format_date,
    format_time,
    get_callout,
    get_date,
    get_file,
    get_heading,
    get_icon,
    get_multi_select,
    get_number,
    get_quote,
    get_rich_text,
    get_select,
    get_table_of_contents,
    get_title,
    get_url,
)

WEREAD_URL = "https://weread.qq.com/"
WEREAD_NOTEBOOKS_URL = "https://i.weread.qq.com/user/notebooks"
WEREAD_BOOKMARKLIST_URL = "https://i.weread.qq.com/book/bookmarklist"
WEREAD_CHAPTER_INFO = "https://i.weread.qq.com/book/chapterInfos"
WEREAD_READ_INFO_URL = "https://i.weread.qq.com/book/readinfo"
WEREAD_REVIEW_LIST_URL = "https://i.weread.qq.com/review/list"
WEREAD_BOOK_INFO = "https://i.weread.qq.com/book/info"
BOOKMARK_ICON_URL = "https://www.notion.so/icons/bookmark_gray.svg"

"""这段Pro里没有"""
def parse_cookie_string(cookie_string):
    cookie = SimpleCookie()
    cookie.load(cookie_string)
    cookies_dict = {}
    cookiejar = None
    for key, morsel in cookie.items():
        cookies_dict[key] = morsel.value
        cookiejar = cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
    return cookiejar


def get_bookmark_list(bookId):
    """获取我的划线"""
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)
    if r.ok:
        updated = r.json().get("updated")
        updated = sorted(
            updated,
            key=lambda x: (x.get("chapterUid", 1), int(x.get("range").split("-")[0])),
        )
        return r.json()["updated"]
    return None


def get_read_info(bookId):
    params = dict(bookId=bookId, readingDetail=1, readingBookIndex=1, finishedDate=1)
    r = session.get(WEREAD_READ_INFO_URL, params=params)
    if r.ok:
        return r.json()
    return None


def get_bookinfo(bookId):
    """获取书的详情"""
    params = dict(bookId=bookId)
    r = session.get(WEREAD_BOOK_INFO, params=params)
    isbn = ""
    if r.ok:
        data = r.json()
        isbn = data["isbn"]
        newRating = data["newRating"] / 1000
        return (isbn, newRating)
    else:
        print(f"get {bookId} book info failed")
        return ("", 0)


def get_review_list(bookId):
    """获取笔记"""
    params = dict(bookId=bookId, listType=11, mine=1, syncKey=0)
    r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
    reviews = r.json().get("reviews")
    summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
    reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
    reviews = list(map(lambda x: x.get("review"), reviews))
    reviews = list(map(lambda x: {**x, "markText": x.pop("content")}, reviews))
    return summary, reviews


def check(bookId):
    """检查是否已经插入过 如果已经插入了就删除"""
    time.sleep(0.3)
    filter = {"property": "Books ID", "rich_text": {"equals": bookId}}
    response = client.databases.query(database_id=database_id, filter=filter)
    for result in response["results"]:
        time.sleep(0.3)
        client.blocks.delete(block_id=result["id"])


def get_chapter_info(bookId):
    """获取章节信息"""
    body = {"bookIds": [bookId], "synckeys": [0], "teenmode": 0}
    r = session.post(WEREAD_CHAPTER_INFO, json=body)
    if (
        r.ok
        and "data" in r.json()
        and len(r.json()["data"]) == 1
        and "updated" in r.json()["data"][0]
    ):
        update = r.json()["data"][0]["updated"]
        return {item["chapterUid"]: item for item in update}
    return None


def insert_to_notion(bookName, bookId, cover, sort, author, isbn, rating, categories):
    """插入到notion"""
    time.sleep(0.3)
    parent = {"database_id": database_id, "type": "database_id"}
    properties = {
        "Books Name":get_title(bookName),
        "Books ID": get_rich_text(bookId),
        "ISBN": get_rich_text(isbn),
        "Resource": get_url(f"https://weread.qq.com/web/reader/{calculate_book_str_id(bookId)}"),
        #"Author": get_rich_text(author),
        "Author": get_select(author),
        "Sort": get_number(sort),
        #这行Pro里没有，"Rating": get_number(rating),注释掉
        "Cover": get_file(cover),
    }
    if categories != None:
        properties["Tags"] =get_multi_select(categories)
    read_info = get_read_info(bookId=bookId)
    if read_info != None:
        markedStatus = read_info.get("markedStatus", 0)
        readingTime = format_time(read_info.get("readingTime", 0))#这行是从pro复制过来的
        """readingTime = read_info.get("readingTime", 0)这行是原版的,搭配163行一起修改"""
        readingProgress = (
            100 if (markedStatus == 4) else read_info.get("readingProgress", 0)
        )#这行是从pro复制过来的,修改了readingProgress的计算方式
        """readingProgress = read_info.get("readingProgress", 0)这行是原版的"""
        totalReadDay = read_info.get("totalReadDay", 0)#这行是从pro复制过来的,新增阅读天数统计，搭配163行一起添加

        """原版的format_time：
        format_time = ""
        hour = readingTime // 3600
        if hour > 0:
            format_time += f"{hour}h"
        minutes = readingTime % 3600 // 60
        if minutes > 0:
            format_time += f"{minutes}min"注释掉"""

        properties["Status"] = {"status": {"name": "Read" if markedStatus == 4 else "Reading"}}#这行是从pro复制过来的
        """properties["Status"] = get_select("Read" if markedStatus == 4 else "Reading")这行是原版的"""
        properties["Time Statistic"] = get_rich_text(readingTime)#这行是从pro复制过来的
        """properties["Time Statistic"] = get_rich_text(format_time)这行是原版的,搭配145行一起修改"""
        properties["Progress"] = {"number": readingProgress / 100}#这行是从pro复制过来的
        properties["DaysCounter"] = {"number": totalReadDay}#这行是从pro复制过来的,新增阅读天数统计，搭配150行一起添加
        """properties["Progress"] = get_number(readingProgress)这行是原版的,搭配()一起修改"""
        
        """ 原版的阅读结束日期计算方法：
            if "finishedDate" in read_info:
            properties["Finish"] = get_date(datetime.utcfromtimestamp(
                        read_info.get("finishedDate")
                    ).strftime("%Y-%m-%d %H:%M:%S"))"""
        
        """下面这段直到（……先注释掉）都是pro复制过来的，新增（开始日期 + 上一次阅读日期 + 结束日期）计算方法，关注一下使用的变量在之前有没有赋值"""
        finishedDate = int(datetime.timestamp(datetime.now()))
        if "finishedDate" in read_info:
            finishedDate = read_info.get("finishedDate")
        elif "readDetail" in read_info:
            if "lastReadingDate" in read_info.get("readDetail"):
                finishedDate = read_info.get("readDetail").get("lastReadingDate")
                lastReadingDate = datetime.utcfromtimestamp(
                    read_info.get("readDetail").get("lastReadingDate")
                ) + timedelta(hours=8)
                properties["Last"] = get_date(
                    #lastReadingDate.strftime("%Y-%m-%d %H:%M:%S")
                    lastReadingDate.strftime("%Y-%m-%d")
                )
        elif "readingBookDate" in read_info:
            finishedDate = read_info.get("readingBookDate")
        finishedDate = datetime.utcfromtimestamp(finishedDate) + timedelta(hours=8)
        properties["Finish"] = get_date(finishedDate.strftime("%Y-%m-%d"))#.strftime("%Y-%m-%d %H:%M:%S"))
        if "readDetail" in read_info and "beginReadingDate" in read_info.get(
            "readDetail"
        ):
            lastReadingDate = datetime.utcfromtimestamp(
                read_info.get("readDetail").get("beginReadingDate")
            ) + timedelta(hours=8)
            properties["Start"] = get_date(
                #lastReadingDate.strftime("%Y-%m-%d %H:%M:%S")
                lastReadingDate.strftime("%Y-%m-%d")
            )
        """新增书籍简介"""
        if (
            read_info.get("bookInfo") != None
            and read_info.get("bookInfo").get("intro") != None
        ):
            properties["Synopsis"] = get_rich_text(read_info.get("bookInfo").get("intro"))
        """notion_helper.get_date_relation(properties,finishedDate)#最后这个像是把阅读结束日期的值传给notion_helper库，不是很清楚，先注释掉"""

    """if cover.startswith("http"):
        icon = get_icon(cover)
    原版没有下面这个else，加一下看是什么
    else:
        icon = get_icon(BOOKMARK_ICON_URL)"""
    icon = get_icon(BOOKMARK_ICON_URL)
    # notion api 限制100个block
    """原版代码"""
    response = client.pages.create(parent=parent, icon=icon, properties=properties)
    id = response["id"]
    return id


def add_children(id, children):
    results = []
    for i in range(0, len(children) // 100 + 1):
        time.sleep(0.3)
        response = client.blocks.children.append(
            block_id=id, children=children[i * 100 : (i + 1) * 100]
        )
        results.extend(response.get("results"))
    return results if len(results) == len(children) else None


def add_grandchild(grandchild, results):
    for key, value in grandchild.items():
        time.sleep(0.3)
        id = results[key].get("id")
        client.blocks.children.append(block_id=id, children=[value])


def get_notebooklist():
    """获取笔记本列表"""
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books")
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None


def get_sort():
    """获取database中的最新时间"""
    filter = {"property": "Sort", "number": {"is_not_empty": True}}
    sorts = [
        {
            "property": "Sort",
            "direction": "descending",
        }
    ]
    response = client.databases.query(
        database_id=database_id, filter=filter, sorts=sorts, page_size=1
    )
    if len(response.get("results")) == 1:
        return response.get("results")[0].get("properties").get("Sort").get("number")
    return 0


def get_children(chapter, summary, bookmark_list):
    children = []
    grandchild = {}
    if chapter != None:
        # 添加目录
        children.append(get_table_of_contents()).left()
        d = {}
        for data in bookmark_list:
            chapterUid = data.get("chapterUid", 1)
            if chapterUid not in d:
                d[chapterUid] = []
            d[chapterUid].append(data)
        for key, value in d.items():
            if key in chapter:
                # 添加章节
                children.append(
                    get_heading(
                        chapter.get(key).get("level"), chapter.get(key).get("title")
                    )
                )
            for i in value:
                if data.get("reviewId") == None and "style" in i and "colorStyle" in i:
                    if i.get("style") not in styles:
                        continue
                    if i.get("colorStyle") not in colors:
                        continue
                markText = i.get("markText")
                for j in range(0, len(markText) // 2000 + 1):
                    children.append(
                        get_callout(
                            markText[j * 2000 : (j + 1) * 2000],
                            i.get("style"),
                            i.get("colorStyle"),
                            i.get("reviewId"),
                        )
                    )
                if i.get("abstract") != None and i.get("abstract") != "":
                    quote = get_quote(i.get("abstract"))
                    grandchild[len(children) - 1] = quote

    else:
        # 如果没有章节信息
        for data in bookmark_list:
            if (
                data.get("reviewId") == None
                and "style" in data
                and "colorStyle" in data
            ):
                if data.get("style") not in styles:
                    continue
                if data.get("colorStyle") not in colors:
                    continue
            markText = data.get("markText")
            for i in range(0, len(markText) // 2000 + 1):
                children.append(
                    get_callout(
                        markText[i * 2000 : (i + 1) * 2000],
                        data.get("style"),
                        data.get("colorStyle"),
                        data.get("reviewId"),
                    )
                )
    if summary != None and len(summary) > 0:
        children.append(get_heading(1, "点评"))
        for i in summary:
            content = i.get("review").get("content")
            for j in range(0, len(content) // 2000 + 1):
                children.append(
                    get_callout(
                        content[j * 2000 : (j + 1) * 2000],
                        i.get("style"),
                        i.get("colorStyle"),
                        i.get("review").get("reviewId"),
                    )
                )
    return children, grandchild


def transform_id(book_id):
    id_length = len(book_id)

    if re.match("^\d*$", book_id):
        ary = []
        for i in range(0, id_length, 9):
            ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
        return "3", ary

    result = ""
    for i in range(id_length):
        result += format(ord(book_id[i]), "x")
    return "4", [result]


def calculate_book_str_id(book_id):
    md5 = hashlib.md5()
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    for i in range(len(transformed_ids)):
        hex_length_str = format(len(transformed_ids[i]), "x")
        if len(hex_length_str) == 1:
            hex_length_str = "0" + hex_length_str

        result += hex_length_str + transformed_ids[i]

        if i < len(transformed_ids) - 1:
            result += "g"

    if len(result) < 20:
        result += digest[0 : 20 - len(result)]

    md5 = hashlib.md5()
    md5.update(result.encode("utf-8"))
    result += md5.hexdigest()[0:3]
    return result


def download_image(url, save_dir="cover"):
    # 确保目录存在，如果不存在则创建
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 获取文件名，使用 URL 最后一个 '/' 之后的字符串
    file_name = url.split("/")[-1] + ".jpg"
    save_path = os.path.join(save_dir, file_name)

    # 检查文件是否已经存在，如果存在则不进行下载
    if os.path.exists(save_path):
        print(f"File {file_name} already exists. Skipping download.")
        return save_path

    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
        print(f"Image downloaded successfully to {save_path}")
    else:
        print(f"Failed to download image. Status code: {response.status_code}")
    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("weread_cookie")
    parser.add_argument("notion_token")
    parser.add_argument("database_id")
    parser.add_argument("ref")
    parser.add_argument("repository")
    parser.add_argument("--styles", nargs="+", type=int, help="划线样式")
    parser.add_argument("--colors", nargs="+", type=int, help="划线颜色")
    options = parser.parse_args()
    weread_cookie = options.weread_cookie
    database_id = options.database_id
    notion_token = options.notion_token
    ref = options.ref
    branch = ref.split("/")[-1]
    repository = options.repository
    styles = options.styles
    colors = options.colors
    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    client = Client(auth=notion_token, log_level=logging.ERROR)
    session.get(WEREAD_URL)
    latest_sort = get_sort()
    books = get_notebooklist()
    if books != None:
        for index, book in enumerate(books):
            sort = book["sort"]
            if sort <= latest_sort:
                continue
            book = book.get("book")
            title = book.get("title")
            cover = book.get("cover")
            if book.get("author") == "公众号" and book.get("cover").endswith("/0"):
                cover += ".jpg"
            if cover.startswith("http") and not cover.endswith(".jpg"):
                path = download_image(cover)
                cover = (
                    f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"
                )
            bookId = book.get("bookId")
            author = book.get("author")
            categories = book.get("categories")
            if categories != None:
                categories = [x["title"] for x in categories]
            print(f"正在同步 {title} ,一共{len(books)}本，当前是第{index+1}本。")
            check(bookId)
            isbn, rating = get_bookinfo(bookId)
            id = insert_to_notion(
                title, bookId, cover, sort, author, isbn, rating, categories
            )
            chapter = get_chapter_info(bookId)
            bookmark_list = get_bookmark_list(bookId)
            summary, reviews = get_review_list(bookId)
            bookmark_list.extend(reviews)
            bookmark_list = sorted(
                bookmark_list,
                key=lambda x: (
                    x.get("chapterUid", 1),
                    0
                    if (x.get("range", "") == "" or x.get("range").split("-")[0] == "")
                    else int(x.get("range").split("-")[0]),
                ),
            )
            children, grandchild = get_children(chapter, summary, bookmark_list)
            results = add_children(id, children)
            if len(grandchild) > 0 and results != None:
                add_grandchild(grandchild, results)
