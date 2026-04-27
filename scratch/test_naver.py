import urllib.parse
import requests

def test_naver(query):
    try:
        enc_query = urllib.parse.quote(query.encode('euc-kr'))
        url = f"https://ac.finance.naver.com/ac?q={enc_query}&q_enc=euc-kr&st=111&r_format=json&r_enc=euc-kr&r_unicode=0&t_koreng=1&type=pc"
        resp = requests.get(url, timeout=3)
        print(f"EUC-KR Status: {resp.status_code}")
        print(f"EUC-KR Output: {resp.text}")
        
        enc_utf8 = urllib.parse.quote(query)
        url_utf8 = f"https://ac.finance.naver.com/ac?q={enc_utf8}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1&type=pc"
        resp_utf8 = requests.get(url_utf8, timeout=3)
        print(f"UTF-8 Status: {resp_utf8.status_code}")
        print(f"UTF-8 Output: {resp_utf8.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_naver("카카오")
