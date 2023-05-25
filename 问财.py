import execjs
import requests
import json
import re
from lxml import etree
import datetime

"""
取到异动大于等于3次的002股票后取其最近公告的发布时间，
然后根据这个时间计算应该计算几天的偏离值
同时取到深指指数涨幅信息，
进行计算

"""

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


def data_clean(code, last_publish_time, r_399107):
    position = ""
    for i in r_399107:
        if last_publish_time == r_399107[i]['date']:
            position = i
    if position == '1':
        # 取标的的近2日涨幅
        sum_399107 = r_399107['1']['inc'] + r_399107['2']['inc']
        data = get_answer(code + '近1个交易日的涨幅', "stock")
        sum_target = data['data']['answer'][0]['txt'][0]['content']['components'][6]['data'][0]['涨跌幅'] + data['data']['answer'][0]['txt'][0]['content']['components'][6]['data'][1]['涨跌幅']
        deviation = round(sum_target - sum_399107, 2)
        print(deviation)
        print(f"若明日涨停不停牌需指数涨幅大于{str(deviation - 20)}")

    elif position == '2':
        # 取标的的近1日涨幅
        sum_399107 = r_399107['2']['inc']
        data = get_answer(code + '近1个交易日的涨幅', "stock")
        sum_target = data['data']['answer'][0]['txt'][0]['content']['components'][6]['data'][0]['涨跌幅']
        deviation = round(sum_target - sum_399107, 2)
        print(deviation)
        print(f"若明日涨停不停牌需指数涨幅大于{str(deviation - 10)}")

    else:
        print("无")

def main():
    # 获取深指3日涨幅
    result_399107_3days = get_answer('399107近3日涨幅', 'zhishu')
    end = len(result_399107_3days['data']['answer'][0]['txt'][0]['content']['components'][1]['data'])
    begin = end - 3
    count = 0
    r_399107 = {0: {}, 1: {}, 2: {}}
    for i in range(begin, end):
        inc = result_399107_3days['data']['answer'][0]['txt'][0]['content']['components'][1]['data'][i]['y']
        r_399107[count]['inc'] = round(float(inc), 2)
        date = result_399107_3days['data']['answer'][0]['txt'][0]['content']['components'][1]['data'][i]['x']
        r_399107[count]['date'] = datetime.datetime.strptime(str(date), "%Y%m%d")
        count += 1
    print(r_399107)

    # 获取已经3次异动的股票
    data = get_answer('近20个交易日涨幅大于50%', 'stock')
    result = data['data']['answer'][0]['txt'][0]['content']['components'][0]['data']['datas']
    for i in result:
        if i['股票代码'].startswith("00"):
            print(i['股票简称'])
            count, last_publish_time = get_notice(i['code'])
            if count > 1:
                data_clean(i['code'], last_publish_time, r_399107)

    data_clean(result, last_publish_time, r_399107)


if __name__ == '__main__':
    time = get_server_time()
    main()
    session.close()
