import execjs
import requests
import json
import re
from lxml import etree
import datetime
from collections import Counter

session = requests.session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
}
session.headers = headers
today = datetime.datetime.now()
str_today = today.strftime('%Y-%m-%d')
start_day = datetime.datetime.now() + datetime.timedelta(days=-31)
str_start_day = start_day.strftime('%Y-%m-%d')


def get_server_time():
    url = 'http://www.iwencai.com/unifiedwap/home/index'
    resp = session.get(url)
    resp_text = resp.text
    tree = etree.HTML(resp_text)
    js_url = "http:" + tree.xpath("//script[1]/@src")[0]
    resp.close()
    js_resp = session.get(js_url)
    js_text = js_resp.text
    obj = re.compile(r'var TOKEN_SERVER_TIME=(?P<time>.*?);!function')
    server_time = obj.search(js_text).group('time')
    return server_time


def get_hexin_v(time):
    f = open("kou.js", "r", encoding='utf-8')
    js_content = f.read()
    js_content = 'var TOKEN_SERVER_TIME=' + str(time) + ";\n" + js_content
    js = execjs.compile(js_content)
    v = js.call("rt.updata")
    return v


def get_answer(question, secondary_intent):
    url = 'http://www.iwencai.com/customized/chart/get-robot-data'

    data = {
        'add_info': "{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}",
        'block_list': "",
        'log_info': "{\"input_type\":\"typewrite\"}",
        'page': 1,
        'perpage': 50,
        'query_area': "",
        'question': question,
        'rsh': "Ths_iwencai_Xuangu_y1wgpofrs18ie6hdpf0dvhkzn2myx8yq",
        'secondary_intent': secondary_intent,
        'source': "Ths_iwencai_Xuangu",
        'version': "2.0"
    }

    session.headers['hexin-v'] = get_hexin_v(get_server_time())
    session.headers['Content-Type'] = 'application/json'
    resp = session.post(url, data=json.dumps(data))
    result = resp.json()
    resp.close()
    return result


def get_notice(query):
    url = 'http://www.iwencai.com/unifiedwap/unified-wap/v1/information/notice'
    data = {
        'query': query,
        'query_source': 'filter',
        'size': '15',
        'offset': '0',
        'dl': '120',
        'tl': '41',
        'start_time': str_start_day,
        'end_time': str_today,
        'date_range': '5'
    }
    session.headers['hexin-v'] = get_hexin_v(get_server_time())
    session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    resp = session.post(url, data=data)
    result = resp.json()['data']['results']
    count = 0
    year = today.year
    last_publish_time = start_day
    for i in result:
        if '股票交易异常波动公告' in i['title']:
            count += 1
            publish_time = datetime.datetime.strptime(str(year) + i['publish_time'], "%Y%m月%d日")
            if last_publish_time < publish_time:
                last_publish_time = publish_time
    print(count)
    resp.close()
    return count, last_publish_time


def main():
    data = get_answer('今日涨停的股票；非ST；所属概念；连板天数；最终涨停时间', 'stock')
    # data = get_answer('4月21日涨停的股票；非ST；所属概念', 'stock')
    result = data['data']['answer'][0]['txt'][0]['content']['components'][0]['data']['datas']
    big_list = []
    for i in result:
        big_list += i['所属概念'].split(';')
    counter = dict(Counter(big_list))
    to_del = ['融资融券', '转融券标的', '华为概念', '富时罗素概念股', '标普道琼斯A股', '沪股通', '富时罗素概念', '深股通', '国企改革', '地方国企改革']
    for deling in to_del:
        try:
            del counter[deling]
        except:
            pass
    # 将字典转化为元组列表
    tuple_list = [(k, v) for k, v in counter.items()]
    sorted_tuple_list = sorted(tuple_list, key=lambda x: x[1], reverse=True)
    # 生成按所属概念股票数排序的字典
    sorted_dict = {t[0]: t[1] for t in sorted_tuple_list}
    dict_result = {}
    for k, v in sorted_dict.items():
        temp = ''
        if v >= 3:
            list_temp = []
            for it in result:
                if k in it['所属概念']:
                    stock_to_save = {'股票简称': it['股票简称'], '连板天数': it['连续涨停天数[' + today.strftime('%Y%m%d') + ']'],
                                     '最终涨停时间': int(it['最终涨停时间[' + today.strftime('%Y%m%d') + ']'].replace(':', ''))}
                    list_temp.append(stock_to_save)

            sorted_stock_list = sorted(list_temp, key=lambda x: (x['连板天数'], -x['最终涨停时间']), reverse=True)
            for stock in sorted_stock_list:
                temp += stock['股票简称'] + str(stock['连板天数']) + ';'

            old_data = get_answer(f'近10个交易日涨停次数大于3次；非ST；{k}概念', 'stock')
            # old_data = get_answer(f'4月8至4月20日涨停次数大于3次；非ST；{k}概念', 'stock')
            old_drg = old_data['data']['answer'][0]['txt'][0]['content']['components'][0]['data']['datas']
            print(k, temp)
            for dict_drg in old_drg:

                for drg_k, drg_v in dict_drg.items():
                    if '涨停次数' in drg_k:
                        print(dict_drg['股票简称'], drg_v)


if __name__ == '__main__':
    time = get_server_time()
    main()
    session.close()
