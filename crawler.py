from _io import BufferedReader
from datetime import datetime
import gzip
import io
import os
import re
from urllib.parse import urlparse
import urllib.request

import conf
import exif


def __crawl(url, proxy=None, timeout=30):
    try:
        if proxy:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http":proxy}))
        else:
            opener = urllib.request.build_opener()
        response = opener.open(url, timeout=timeout)
        if response.getheader("Content-Encoding") == "gzip":
            return gzip.decompress(response.read())
        else:
            return response.read()
    except Exception as e:
        print(e)
        print("error for url %s" % url)
        return None
    finally:
        try:
            response.close()
        except:
            return None
def crawl(url, charset=None, proxy=conf.proxy, retry=3, timeout=10):
    retry = 1 if retry < 1 else retry
    for i in range(0, retry):
        if i > 0:
            print("retry %d for %s" % (i, url))
        r = __crawl(url, proxy, timeout)
        if r:
            return r if not charset else r.decode(charset)
    return None

update_url = "http://www.x-art.com/updates/"

class regexs:
    meta = "".join([r"<li>[\s]*?<a.*?href=['\"](.*?)['\"][^>]*?>[\s]*?<div class=\"item\" data-equalizer-watch>[\s\S]*?",
                    r"<div class=\"item-img\">[\s]*?<img.*\[(.*?), \(large\)\].*?>[\s\S]*?",
                    r"<h1>(.*?)</h1>[\s]*?<h2>([\s\S]*?)(</h2>)?[\s]*?<h2>(.*?)</h2>[\s\S]*?"])
    rate = r"<h2>(.*?)\(\d+ votes\).*?</h2>"
    model_list = r"<h2><span>featuring</span>((\s*?<a.*?>(.*?)</a>\s*?)*)</h2>"
    model = r"<a.*?>(.*?)</a>"
    comment = r"<cite>\s*?(.*?)\s*?</cite>"

if __name__ == "__main__":
    update_page = crawl(update_url, "utf-8")
    add_cnt = 0
    for m in re.findall(regexs.meta, update_page):
        detail_url = m[0].replace(" ", "%20")
        pic_url = m[1].replace(" ", "%20")
        name, tp, time = m[2], m[3], m[5]
        comment = re.sub(r"<[^>]*>", "", m[5].replace("\n", "").replace("&nbsp;", " "))
        if "first_item" not in locals():
            first_item = "The first item is {%s, %s, %s}" % (name, time, tp.strip())
        if "HD video".lower() not in tp.lower():
            continue
        parse_r = urlparse(pic_url)
        pic_type = parse_r.path[parse_r.path.rfind(".")+1:]
        
        ntime = datetime.strptime(time, "%b %d, %Y").strftime("%Y%m%d")
        pic_name = "%s - %s.%s" % (ntime, name, pic_type)
        pic_abs_path = os.path.join(conf.pic_root, pic_name)
        if not os.path.exists(pic_abs_path) or os.path.getsize(pic_abs_path) == 0:
            print(detail_url)
            detail_page = crawl(detail_url, "utf-8")
            m = re.search(regexs.rate, detail_page)
            rate = m.group(1) if m else None
            m = re.search(regexs.model_list, detail_page)
            model_list = m.group(1) if m else None
            if model_list:
                m = re.findall(regexs.model, model_list)
                models = ", ".join(m) if m else None
            else:
                models = None
            m = re.search(regexs.comment, detail_page)
            comment = m.group(1) if m else None
            if comment:
                comment = re.sub(r"<[^>]*>", "", comment.strip().replace("\n", "").replace("&nbsp;", " "))
            print("saving pic: %s location: %s" % (pic_url, pic_name))
            print("\tmodels:%s comment:%s rate:%s" % (models, comment, rate))
            add_cnt += 1
            img_data = crawl(pic_url)
            with open(pic_abs_path, "wb") as wp:
                exif.copy_on_write(io.BytesIO(img_data), wp, {"model":models, "rate":rate, "desc":comment})
    if add_cnt == 0:
        print("first item is %s" % first_item)
    print("total add %d" % add_cnt)