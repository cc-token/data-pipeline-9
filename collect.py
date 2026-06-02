import requests
import time
import json
import os
import sys

API = "https://api.csqaq.com"
HDR = lambda token: {"ApiToken": token, "User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

CHART_CONFIGS = []
for pid, prefix in [[1, "buff"], [2, "yyyp"]]:
    for period in [365, 30, 7, 90, 180]:
        for key in ["sell_price", "sell_num", "buy_num", "buy_price"]:
            CHART_CONFIGS.append({"data_key": f"{prefix}_{key}_{period}d", "key": key, "platform": pid, "period": period})

TOKENS = [t.strip() for t in os.environ.get("CSQAQ_TOKENS", "").split(",") if t.strip()]


def collect_item(text, token, goods_id=None):
    print(f"采集: {text}, token={token[:8]}...")

    print(f"[1/3] bind...")
    bind_r = requests.post(f"{API}/api/v1/sys/bind_local_ip", headers=HDR(token)).json()
    print(f"  bind: code={bind_r.get('code')}")
    if bind_r.get("code") != 200:
        print(f"  bind失败: {bind_r}")
        return {"name": text, "chart_ok": 0, "chart_fail": 40, "error": "bind_failed"}

    bind_ip_raw = bind_r.get("data", "")
    bind_ip = bind_ip_raw.split("\uff1a")[-1].strip() if "\uff1a" in bind_ip_raw else bind_ip_raw.strip()
    print(f"  绑定IP: {bind_ip}")
    time.sleep(5)

    name = text

    if not goods_id:
        print(f"[2/3] search...")
        search_r = requests.get(f"{API}/api/v1/search/suggest?text={text}", headers=HDR(token)).json()
        if search_r.get("code") != 200:
            print(f"  search失败: {search_r}")
            return {"name": text, "chart_ok": 0, "chart_fail": 40, "error": "search_failed"}

        search_data = search_r.get("data", [])
        if not search_data:
            return {"name": text, "chart_ok": 0, "chart_fail": 40, "error": "not_found"}

        normal = [it for it in search_data if "StatTrak" not in it.get("value", "")]
        selected = normal[0] if normal else search_data[0]
        goods_id = selected["id"]
        name = selected["value"]
        print(f"  找到: {name} (id={goods_id})")
        time.sleep(1.1)
    else:
        print(f"[2/3] 跳过search, 直接使用goods_id={goods_id}")

    print(f"[3/3] detail...")
    detail_data = None
    try:
        detail_r = requests.get(f"{API}/api/v1/info/good?id={goods_id}", headers=HDR(token)).json()
        if detail_r.get("code") == 200:
            detail_data = detail_r.get("data")
            if detail_data and detail_data.get("market_hash_name"):
                name = detail_data["market_hash_name"]
    except:
        pass
    time.sleep(1.1)

    print(f"[3/3] chart (40个)...")
    chart_data = {}
    chart_ok = 0
    chart_fail = 0

    for i, cfg in enumerate(CHART_CONFIGS):
        try:
            r = requests.post(f"{API}/api/v1/info/chart", headers=HDR(token),
                              json={"good_id": str(goods_id), "key": cfg["key"], "platform": cfg["platform"], "period": cfg["period"], "style": "all_style"}).json()
            if r.get("code") == 200:
                chart_data[cfg["data_key"]] = r.get("data")
                chart_ok += 1
            else:
                chart_data[cfg["data_key"]] = None
                chart_fail += 1
        except:
            chart_data[cfg["data_key"]] = None
            chart_fail += 1

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/40] {chart_ok}OK/{chart_fail}FAIL")
        if i < len(CHART_CONFIGS) - 1:
            time.sleep(1.2)

    print(f"  结果: {chart_ok}OK/{chart_fail}FAIL ({chart_ok/40*100:.0f}%)")

    return {
        "name": name,
        "goods_id": goods_id,
        "bind_ip": bind_ip,
        "detail": detail_data,
        "chart": chart_data,
        "chart_ok": chart_ok,
        "chart_fail": chart_fail,
    }


def main():
    text = ""
    goods_id = None
    token_index = 0

    for i, arg in enumerate(sys.argv):
        if arg == "--text" and i + 1 < len(sys.argv):
            text = sys.argv[i + 1]
        if arg == "--goods-id" and i + 1 < len(sys.argv):
            goods_id = sys.argv[i + 1]
        if arg == "--token-index" and i + 1 < len(sys.argv):
            token_index = int(sys.argv[i + 1])

    if not text and not goods_id:
        print("错误: 缺少 --text 或 --goods-id 参数")
        sys.exit(1)

    if not text:
        text = f"item_{goods_id}"

    if not TOKENS:
        print("错误: 未设置CSQAQ_TOKENS环境变量")
        sys.exit(1)

    token = TOKENS[token_index % len(TOKENS)]
    print(f"CSQAQ采集: {text}, goods_id={goods_id}, token_index={token_index}, token={token[:8]}...")

    result = collect_item(text, token, goods_id=goods_id)

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"保存: result.json")


if __name__ == "__main__":
    main()
