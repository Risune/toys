import os
import re

import conf
import exif


def read_info(root):
    infos = []
    for item in os.listdir(root):
        with open(os.path.join(root, item), "rb") as fp:
            info = exif.parse_exif(fp)
            m = re.match(r"(\d{8}) \- (.+).jpg", item)
            if m:
                info["time"] = m.group(1)
                info["name"] = m.group(2)
                infos.append(info)
    return infos

def info2name(info):
    return "%s - %s - %s" % (info["time"], info["name"], info["model"])

def guess_name(infos, fn):
    idx = fn.rfind(".")
    name = fn[0:idx]
    ext = fn[idx+1:]
    tokens = do_seg(name.lower())
    
    new_name = None
    max_score = 0
    for info in infos:
        ts = do_seg(info["name"].lower())
        score = len(ts & tokens) * 100 / (len(tokens) + 10)
        if score > max_score:
            max_score = score
            new_name = "%s.%s" % (info2name(info), ext)
    return new_name

ignore_tokens = ["x-art", "-"]
def do_seg(s):
    raw = re.findall(r"[a-z0-9\-]+", s)
    for banned in ignore_tokens:
        if banned in raw:
            raw.remove(banned)
    return set(raw)

if __name__ == "__main__":
    infos = read_info(conf.pic_root)
    
    for fn in os.listdir(conf.root):
        abs_path = os.path.join(conf.root, fn)
        if os.path.isfile(abs_path):
            new_name = guess_name(infos, fn)
            if not new_name:
                print("%s not matched" % fn)
            else:
                new_abs_path = os.path.join(conf.root, new_name)
                if new_name != fn and not os.path.exists(new_abs_path):
                    os.renames(abs_path, new_abs_path)
                    print("%s --> %s" % (fn, new_name))
    
    statistic = {"true":0, "never":0, "undefined":0, "dup":0}
    for info in infos:
        if "status" in info and info["status"] in statistic:
            statistic[info["status"]] += 1
        else:
            name = info2name(info)
            for fn in os.listdir(conf.root):
                if os.path.isfile(os.path.join(conf.root, fn)):
                    if fn.startswith(name):
                        # update
                        pic_name = "%s - %s.%s" % (info["time"], info["name"], "jpg")
                        pic_abs_path = os.path.join(conf.pic_root, pic_name) 
                        tmp_abs_path = "%s.tmp" % pic_abs_path
                        with open(pic_abs_path, "rb") as fp:
                            exif_meta = exif.parse_exif(fp)
                            exif_meta["status"] = "true"
                        with open(pic_abs_path, "rb") as rp:
                            with open(tmp_abs_path, "wb") as wp:
                                exif.copy_on_write(rp, wp, exif_meta)                              
                        os.remove(pic_abs_path)
                        os.renames(tmp_abs_path, pic_abs_path)
                        statistic["true"] += 1  
                        break
            else:
                statistic["undefined"] += 1
    print(statistic)