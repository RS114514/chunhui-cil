#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import re
import time
import urllib.parse

# Ensure we can import ch_cli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import ch_cli

def out_json(success, data):
    print(json.dumps({"success": success, "data": data}, ensure_ascii=False))
    sys.exit(0)

def require_args(cmd, min_args, usage):
    if len(sys.argv) < min_args:
        out_json(False, f"参数错误: 用法 {usage}")

def parse_grade(grade):
    try:
        value = int(grade)
    except (TypeError, ValueError):
        out_json(False, "参数错误: 年级必须是数字")
    if value not in (1, 2, 3):
        out_json(False, "参数错误: 年级必须是 1、2 或 3")
    return value

def bridge_login(cookie):
    sessionid = ""
    csrftoken = ""
    parts = [p.strip() for p in cookie.split(";")]
    for part in parts:
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k == "sessionid":
                sessionid = v
            elif k == "csrftoken":
                csrftoken = v
    session_data = {
        "sessionid": sessionid,
        "csrftoken": csrftoken
    }
    if ch_cli.save_session(session_data):
        status, _, _ = ch_cli.make_request("/article/article-detail/37079/", method="GET")
        if status == 200:
            out_json(True, "登录成功")
        else:
            out_json(False, f"会话校验失败 (HTTP: {status})")
    else:
        out_json(False, "保存会话文件失败")

def bridge_status():
    cookies = ch_cli.load_session()
    if not cookies.get("sessionid"):
        out_json(False, "未登录")
        return
    status, _, _ = ch_cli.make_request("/article/article-detail/37079/", method="GET")
    if status == 200:
        out_json(True, "登录有效")
    else:
        out_json(False, "会话失效")

def bridge_messages(page):
    url = f"/sitemessage/message-Receive-list/?page={page}"
    status, body, _ = ch_cli.make_request(url, method="GET")
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html_content = body.decode("utf-8", errors="ignore")
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    trs = tr_pattern.findall(html_content)
    rows = []
    for tr in trs:
        if "show-Message" in tr:
            id_m = re.search(r'/sitemessage/show-Message/(\d+)/\s*', tr)
            msg_id = id_m.group(1) if id_m else ""
            if not msg_id:
                id_m = re.search(r'del_siteMessage\(this,(\d+)\)', tr)
                if id_m:
                    msg_id = id_m.group(1)
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            if len(tds) >= 3:
                title = ch_cli.clean_html(tds[1])
                sender = ch_cli.clean_html(tds[2])
                date = ch_cli.clean_html(tds[3]) if len(tds) > 3 else ""
                rows.append({"id": msg_id, "title": title, "sender": sender, "date": date})
    out_json(True, rows)

def bridge_message_detail(msg_id):
    status, body, _ = ch_cli.make_request(f"/sitemessage/show-Message/{msg_id}/", method="GET")
    if status != 200:
        out_json(False, f"获取详情失败 (HTTP: {status})")
    html_content = body.decode("utf-8", errors="ignore")
    title = "无标题"
    title_m = re.search(r'<div class="ArticleTitle">(.*?)</div>', html_content, re.DOTALL)
    if title_m:
        title = ch_cli.clean_html(title_m.group(1))
    sender = "未知"
    sender_m = re.search(r'发送者：\s*([^\s<]+)', html_content)
    if sender_m:
        sender = sender_m.group(1).strip()
    send_time = "未知"
    time_m = re.search(r'发送时间：\s*([^\s<]+(?:\s+[^\s<]+)?)', html_content)
    if time_m:
        send_time = time_m.group(1).strip()
    content = ""
    content_m = re.search(r'<div class="ArticleContent[^>]*>(.*?)</div>\s*</div>', html_content, re.DOTALL)
    if not content_m:
        content_m = re.search(r'<div class="ArticleContent[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if content_m:
        content = ch_cli.render_html_to_markdown(content_m.group(1))
    links = ch_cli.extract_attachment_links(html_content)
    out_json(True, {
        "title": title,
        "sender": sender,
        "time": send_time,
        "content": content,
        "attachments": links
    })

def bridge_news(col_id, page):
    status, body, _ = ch_cli.make_request(f"/article/column-detail/{col_id}/?page={page}", method="GET", follow_redirects=True)
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html_content = body.decode("utf-8", errors="ignore")
    items = re.findall(r'href=["\']/article/article-detail/(\d+)/["\'][^>]*>\s*(.*?)\s*</a>.*?class="[^"]*text-secondary"[^>]*>\s*(.*?)\s*</div>', html_content, re.DOTALL)
    rows = []
    for art_id, title, date in items:
        rows.append({"id": art_id, "title": ch_cli.clean_html(title), "date": ch_cli.clean_html(date)})
    out_json(True, rows)

def bridge_news_detail(art_id):
    status, body, _ = ch_cli.make_request(f"/article/article-detail/{art_id}/", method="GET", follow_redirects=True)
    if status != 200:
        out_json(False, f"获取详情失败 (HTTP: {status})")
    html_content = body.decode("utf-8", errors="ignore")
    title = "无标题"
    title_m = re.search(r'<div class="ArticleTitle[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if title_m:
        title = ch_cli.clean_html(title_m.group(1))
    source = "未知"
    source_m = re.search(r'来源：\s*([^<]+)', html_content)
    if source_m:
        source = ch_cli.clean_html(source_m.group(1))
    pub_time = "未知"
    time_m = re.search(r'发布时间：\s*([^\s<]+(?:\s+[^\s<]+)?)', html_content)
    if time_m:
        pub_time = time_m.group(1).strip()
    content = ""
    content_m = re.search(r'<div class="ArticleContent(?:\s+[^>]*|)\s*>(.*?)</div>', html_content, re.DOTALL)
    if content_m:
        content = ch_cli.render_html_to_markdown(content_m.group(1))
    links = ch_cli.extract_attachment_links(html_content)
    out_json(True, {
        "title": title,
        "source": source,
        "time": pub_time,
        "content": content,
        "attachments": links
    })

def bridge_hygiene(page):
    status, body, _ = ch_cli.make_request(f"/classappraise/hygienePictures_receive_list/?page={page}", method="GET")
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html_content = body.decode("utf-8", errors="ignore")
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    trs = tr_pattern.findall(html_content)
    rows = []
    for tr in trs:
        if "show-Message" in tr:
            id_m = re.search(r'/classappraise/show-Message/(\d+)/\s*', tr)
            record_id = id_m.group(1) if id_m else ""
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            if len(tds) >= 4:
                location = ch_cli.clean_html(tds[1])
                description = ch_cli.clean_html(tds[2])
                date = ch_cli.clean_html(tds[3])
                rows.append({"id": record_id, "location": location, "description": description, "date": date})
    out_json(True, rows)

def bridge_hygiene_detail(record_id):
    status, body, _ = ch_cli.make_request(f"/classappraise/show-Message/{record_id}/", method="GET")
    if status != 200:
        out_json(False, f"获取考评明细失败 (HTTP: {status})")
    html_content = body.decode("utf-8", errors="ignore")
    desc = "未知违纪说明"
    content_m = re.search(r'<div class="ArticleContent[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if content_m:
        desc = ch_cli.render_html_to_markdown(content_m.group(1))
    recipients_all = "无"
    rec1_m = re.search(r'id="multiCollapseExample1">\s*<div class="card card-body">\s*(.*?)\s*</div>', html_content, re.DOTALL)
    if rec1_m:
        recipients_all = ch_cli.clean_html(rec1_m.group(1))
    media_urls = []
    imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html_content)
    for img in imgs:
        if "Logo" not in img and "newFunc" not in img and "sydw" not in img:
            if not img.startswith("http") and img.startswith("/"):
                media_urls.append(f"{ch_cli.BASE_URL}{img}")
            else:
                media_urls.append(img)
    vids = re.findall(r'<video[^>]+src=["\'](.*?)["\']', html_content)
    for vid in vids:
        if not vid.startswith("http") and vid.startswith("/"):
            media_urls.append(f"{ch_cli.BASE_URL}{vid}")
        else:
            media_urls.append(vid)
    out_json(True, {
        "description": desc,
        "recipients": recipients_all,
        "media": media_urls
    })

def bridge_bedroom_class(grade, class_name):
    res = ch_cli.find_class_id(parse_grade(grade), class_name)
    if not res:
        out_json(False, f"未找到匹配班级 \"{class_name}\"")
    class_id, class_name = res
    post_data = {
        "chGradeIDForName": str(grade),
        "chClassIDForName": class_id
    }
    status, body, _ = ch_cli.make_request("/classappraise/QueryBedroomsByClassID_JustForView/", method="POST", data=post_data)
    if status != 200:
        out_json(False, f"请求失败 (HTTP: {status})")
    html = body.decode("utf-8", errors="ignore")
    alert_m = re.search(r'class="alert alert-primary"[^>]*>\s*(.*?)\s*</div>', html, re.DOTALL)
    if alert_m:
        out_json(True, {
            "class_name": class_name,
            "result": ch_cli.clean_html(alert_m.group(1))
        })
    else:
        out_json(False, "未查到该班级的寝室分配数据。")

def bridge_bedroom_hygiene(dorm, start, end, show_all):
    post_data = {
        "chDormitoryForName": dorm,
        "theBeginDateForName": start,
        "theEndDateForName": end
    }
    status, body, _ = ch_cli.make_request("/classappraise/BedRoom_DisciplineHygiene_JustForView/", method="POST", data=post_data)
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html = body.decode("utf-8", errors="ignore")
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    trs = tr_pattern.findall(html)
    rows = []
    for tr in trs:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
        if len(tds) >= 4:
            room = ch_cli.clean_html(tds[0])
            cls_name = ch_cli.clean_html(tds[1])
            hyg = ch_cli.clean_html(tds[2]) or "0"
            disc = ch_cli.clean_html(tds[3]) or "0"
            total = ch_cli.clean_html(tds[4]) if len(tds) > 4 else "0"
            if show_all == 'false' or show_all is False:
                if not total or total.strip() == "" or total.strip() == "0":
                    continue
            rows.append({"room": room, "class": cls_name, "hygiene": hyg, "discipline": disc, "total": total})
    out_json(True, rows)

def bridge_duty(search_query, show_all):
    status, body, _ = ch_cli.make_request("/classappraise/TeacherDutyWeek_JustForView/", method="GET")
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html = body.decode("utf-8", errors="ignore")
    blocks = re.findall(r'<ul class="list-group"\s*>(.*?)</ul>', html, re.DOTALL)
    duties = []
    for block in blocks:
        is_current = "list-group-item-success" in block
        lis = re.findall(r'<li[^>]*>(.*?)</li>', block, re.DOTALL)
        if not lis:
            continue
        week_name = re.sub(r'<[^>]+>', '', lis[0]).strip()
        date_range = re.sub(r'<[^>]+>', '', lis[1]).strip() if len(lis) > 1 else ""
        details = {}
        for li in lis[2:]:
            clean = re.sub(r'<[^>]+>', '', li).strip()
            if "：" in clean:
                k, v = clean.split("：", 1)
                details[k.strip()] = v.strip()
        info = {
            "is_current": is_current,
            "week": week_name,
            "date": date_range,
            "admin": details.get("行政值周", ""),
            "group1": details.get("第一小组", ""),
            "group2": details.get("第二小组", ""),
            "group3": details.get("第三小组", ""),
            "class": details.get("值周班级", ""),
            "talk": details.get("旗下讲话", "")
        }
        if show_all == 'true' or show_all is True or is_current:
            if search_query:
                q = search_query.lower()
                matches = (q in info["admin"].lower() or 
                           q in info["group1"].lower() or 
                           q in info["group2"].lower() or 
                           q in info["group3"].lower() or 
                           q in info["class"].lower() or 
                           q in info["week"].lower())
                if not matches:
                    continue
            duties.append(info)
    out_json(True, duties)

def bridge_lostfound(page):
    status, body, _ = ch_cli.make_request(f"/lostAndFound/lostAndFoundList/?page={page}", method="GET", follow_redirects=True)
    if status != 200:
        out_json(False, f"HTTP Error: {status}")
    html_content = body.decode("utf-8", errors="ignore")
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    trs = tr_pattern.findall(html_content)
    rows = []
    for tr in trs:
        tds = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', tr, re.DOTALL)
        if len(tds) >= 8 and "类别" not in tds[1]:
            lf_id = ""
            id_m = re.search(r'href=["\']/lostAndFound/lostAndFoundDetail/(\d+)/["\']', tds[2])
            if id_m:
                lf_id = id_m.group(1)
            category = ch_cli.clean_html(tds[1])
            title = ch_cli.clean_html(tds[2])
            reporter = ch_cli.clean_html(tds[3])
            start_date = ch_cli.clean_html(tds[6])
            status_text = ch_cli.clean_html(tds[8]) if len(tds) > 8 else ""
            rows.append({
                "id": lf_id,
                "category": category,
                "title": title,
                "reporter": reporter,
                "date": start_date,
                "status": status_text
            })
    out_json(True, rows)

def bridge_lostfound_detail(lf_id):
    status, body, _ = ch_cli.make_request(f"/lostAndFound/lostAndFoundDetail/{lf_id}/", method="GET", follow_redirects=True)
    if status != 200:
        out_json(False, f"获取详情失败 (HTTP: {status})")
    html_content = body.decode("utf-8", errors="ignore")
    title = "无标题"
    title_m = re.search(r'<div class="ArticleTitle[^>]*>(.*?)</div>', html_content, re.DOTALL)
    if title_m:
        title = ch_cli.clean_html(title_m.group(1))
    reporter = "未知"
    rep_m = re.search(r'来源：\s*([^<]+)', html_content)
    if rep_m:
        reporter = ch_cli.clean_html(rep_m.group(1))
    reviewer = "未知"
    rev_m = re.search(r'审核人：\s*([^<]+)', html_content)
    if rev_m:
        reviewer = ch_cli.clean_html(rev_m.group(1))
    pub_time = "未知"
    time_m = re.search(r'发布时间：\s*([^\s<]+(?:\s+[^\s<]+)?)', html_content)
    if time_m:
        pub_time = time_m.group(1).strip()
    content = ""
    content_m = re.search(r'<div class="ArticleContent(?:\s+[^>]*|)\s*>(.*?)</div>', html_content, re.DOTALL)
    if content_m:
        content = ch_cli.render_html_to_markdown(content_m.group(1))
    media_urls = []
    imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html_content)
    for img in imgs:
        if "Logo" not in img and "newFunc" not in img and "sydw" not in img:
            if not img.startswith("http") and img.startswith("/"):
                media_urls.append(f"{ch_cli.BASE_URL}{img}")
            else:
                media_urls.append(img)
    vids = re.findall(r'<video[^>]+src=["\'](.*?)["\']', html_content)
    for vid in vids:
        if not vid.startswith("http") and vid.startswith("/"):
            media_urls.append(f"{ch_cli.BASE_URL}{vid}")
        else:
            media_urls.append(vid)
    out_json(True, {
        "title": title,
        "reporter": reporter,
        "reviewer": reviewer,
        "time": pub_time,
        "content": content,
        "media": media_urls
    })

def main():
    if len(sys.argv) < 2:
        out_json(False, "参数错误")
    cmd = sys.argv[1]
    
    # Check login first if required, but status and login endpoints don't need auth check
    if cmd == "login":
        require_args(cmd, 3, "login <cookie>")
        bridge_login(sys.argv[2])
    elif cmd == "status":
        bridge_status()
    elif cmd == "messages":
        bridge_messages(sys.argv[2] if len(sys.argv) > 2 else "1")
    elif cmd == "message_detail":
        require_args(cmd, 3, "message_detail <msg_id>")
        bridge_message_detail(sys.argv[2])
    elif cmd == "news":
        require_args(cmd, 3, "news <column_id> [page]")
        bridge_news(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "1")
    elif cmd == "news_detail":
        require_args(cmd, 3, "news_detail <article_id>")
        bridge_news_detail(sys.argv[2])
    elif cmd == "hygiene":
        bridge_hygiene(sys.argv[2] if len(sys.argv) > 2 else "1")
    elif cmd == "hygiene_detail":
        require_args(cmd, 3, "hygiene_detail <record_id>")
        bridge_hygiene_detail(sys.argv[2])
    elif cmd == "bedroom_class":
        require_args(cmd, 4, "bedroom_class <grade> <class_name>")
        bridge_bedroom_class(sys.argv[2], sys.argv[3])
    elif cmd == "bedroom_hygiene":
        require_args(cmd, 5, "bedroom_hygiene <dorm> <start> <end> [show_all]")
        bridge_bedroom_hygiene(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "false")
    elif cmd == "duty":
        bridge_duty(sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] == "true" if len(sys.argv) > 3 else False)
    elif cmd == "lostfound":
        bridge_lostfound(sys.argv[2] if len(sys.argv) > 2 else "1")
    elif cmd == "lostfound_detail":
        require_args(cmd, 3, "lostfound_detail <item_id>")
        bridge_lostfound_detail(sys.argv[2])
    else:
        out_json(False, f"未知命令: {cmd}")

if __name__ == "__main__":
    main()
