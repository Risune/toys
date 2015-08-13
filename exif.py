import os

fields = {b'\x01;':'model', b'\x9c\x9c':'desc', b'\x9c\x9b':'rate', b'\x9c\x9f':'status'}
reversed_fields = dict([(v, k) for k, v in fields.items()])
v_charset = "utf-16le"

def exif(f):
    f.read(2)
    while 1:
        tag = f.read(2)
        l = f.read(2)
        length = b2i(l)
        content = f.read(length-2)
        if len(tag) == 2 and tag[0] == 0xff and tag[1] == 0xe1 and content[0:4] == b'Exif':
            return content[6:]
    return None

def b2i(bs, bigendian=True):
    i = 0
    for idx, b in enumerate(bs):
        if bigendian:
            i = (i << 8) | (b & 0xff)
        else:
            i = i | ((b & 0xff) << (idx * 8))
    return i

def i2b(i):
    bs = bytearray(4)
    for idx in range(0, 4):
        bs[idx] = (i >> (8 * (3 - idx))) & 0xff
    return bs
        

def v2b(v):
    return bytearray((v + "\0").encode(v_charset))

def parse_ifd(raw, offset, bigendian=True):
    result = {}        
    num = b2i(raw[offset:offset+2], bigendian)
    for i in range(0, num):
        ifd = raw[offset+2+i*12:offset+14+i*12]
        tp = b2i(ifd[2:4], bigendian)
        if tp == 1 and ifd[0:2] in fields:
            l = b2i(ifd[4:8], bigendian)
            os = b2i(ifd[8:], bigendian)
            data = raw[os:os+l]
            result[fields[ifd[0:2]]] = data.decode(v_charset)[0:-1]
    return (result, b2i(raw[offset+2+num*12:offset+6+num*12], bigendian))

def parse_exif(fp):
    raw = exif(fp)
    bigendian = raw[0:2] == b'MM'
    offset = b2i(raw[4:8], bigendian)
    while offset > 0:
        result, offset = parse_ifd(raw, offset, bigendian)
        if len(result) > 0:
            return result
    
def create_exif(d):
    num = 0
    for k, v in d.items():
        if k in reversed_fields:
            num += 1
    if num == 0:
        return None
    data_offset = num * 12 + 14 # 12B per ifd, 8 for head, 4 for next pointer, 2 for ifd num
    ifds = bytearray(b"Exif\x00\x00MM\x00\x2a")
    ifds.extend(i2b(8))
    ifds.extend(i2b(num)[2:])
    datas = bytearray()
    for k, v in d.items():
        if k in reversed_fields:
            vb = v2b(d[k])
            datas.extend(vb)
            ifds.extend(reversed_fields[k])
            ifds.extend(b'\x00\x01')
            ifds.extend(i2b(len(vb)))
            ifds.extend(i2b(data_offset))
            data_offset += len(vb)
    else:
        ifds.extend([0] * 4)
    size = len(ifds) + len(datas) + 4
    return b''.join([b'\xff\xe1', i2b(size)[2:], ifds, datas])

def copy_on_write(rp, wp, d):
    exif = create_exif(d)
    while True:
        marker = rp.read(2)
        if marker == b'\xff\xd8':
            wp.write(marker)
            wp.write(exif)
        elif marker == b'\xff\xda':
            wp.write(marker)
            wp.write(rp.read())
            break
        else:
            l = rp.read(2)
            length = b2i(l)
            seg = rp.read(length - 2)
            if marker == b'\xff\xe1' and seg[0:4] == b'Exif':
                pass
            else:
                wp.write(marker)
                wp.write(l)
                wp.write(seg)
        
if __name__ == "__main__":
    with open("d:/1.jpg", "rb") as rp:
        with open("d:/3.jpg", "wb") as wp:
            copy_on_write(rp, wp, {'status': 'true', 'desc': 'HD Video: This is simply the hottest video you will ever see with a threesome containing X-Art exclusive model Alex Grey and little latina legend Veronica Rodriguez! Make sure you have your heart monitor on. This group will have you on your knees begging for more! xoxo Love, Colette', 'model': 'Veronica Rodriguez, Alex Grey'})
