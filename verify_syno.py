import urllib.request
import urllib.parse
import json

IP_PORT = "10.181.201.188:5000"
TOKEN = "zmwdE4vqUthmo"
BASE_URL = f"http://{IP_PORT}/webapi/entry.cgi"

# 1. 测试不传 folder_id（尝试获取全空间照片）
params_all = {
    "api": "SYNO.FotoTeam.Browse.Item",
    "method": "list",
    "version": 1,
    "SynoToken": TOKEN,
    "offset": 0,
    "limit": 50,
    "additional": '["thumbnail", "resolution"]'
}

# 2. 测试特定文件夹（春晖建筑对应的 folder_id 暂定 335 或者是 1 里的子项目）
params_folder = params_all.copy()
params_folder["folder_id"] = 335

def test_api():
    print("====== 共享空间照片接口深度测试 ======")
    
    # 测试 1：不限文件夹获取照片
    print("\n[测试 1]: 获取全共享空间照片 (不传 folder_id) ...")
    query_all = urllib.parse.urlencode(params_all)
    url_all = f"{BASE_URL}?{query_all}"
    req_all = urllib.request.Request(url_all, headers={'User-Agent': 'Mozilla/5.0'})
    
    item_id_to_test = None
    try:
        with urllib.request.urlopen(req_all, timeout=8) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("success"):
                items = res.get("data", {}).get("list", [])
                print(f"✅ 成功！获取到照片数: {len(items)}")
                if items:
                    item_id_to_test = items[0].get("id")
                    print("数据格式样例 (第一张照片):")
                    print(json.dumps(items[0], indent=4, ensure_ascii=False))
            else:
                print("❌ 失败:", res.get("error"))
    except Exception as e:
        print("❌ 发生异常:", e)

    # 测试 2：获取特定文件夹 335
    print("\n[测试 2]: 获取特定文件夹的照片 (folder_id=335) ...")
    query_folder = urllib.parse.urlencode(params_folder)
    url_folder = f"{BASE_URL}?{query_folder}"
    req_folder = urllib.request.Request(url_folder, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req_folder, timeout=8) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("success"):
                items = res.get("data", {}).get("list", [])
                print(f"✅ 成功！该文件夹下照片数: {len(items)}")
                if items and not item_id_to_test:
                    item_id_to_test = items[0].get("id")
                    print("数据格式样例 (该文件夹首张照片):")
                    print(json.dumps(items[0], indent=4, ensure_ascii=False))
            else:
                print("❌ 失败:", res.get("error"))
    except Exception as e:
        print("❌ 发生异常:", e)

    # 测试 3：测试缩略图获取接口
    if item_id_to_test:
        print(f"\n[测试 3]: 测试缩略图获取接口 (基于照片 ID: {item_id_to_test}) ...")
        # 尝试 FotoTeam.Thumbnail 和 Foto.Thumbnail 两个 API
        for thumb_api in ["SYNO.FotoTeam.Thumbnail", "SYNO.Foto.Thumbnail"]:
            thumb_params = {
                "api": thumb_api,
                "method": "get",
                "version": 1,
                "SynoToken": TOKEN,
                "id": item_id_to_test,
                "size": "m"  # m 代表中等大小，或者也可以测 "sm", "xl"
            }
            query_thumb = urllib.parse.urlencode(thumb_params)
            url_thumb = f"{BASE_URL}?{query_thumb}"
            print(f" -> 正在调用: {thumb_api} ...")
            req_thumb = urllib.request.Request(url_thumb, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req_thumb, timeout=5) as response:
                    content_type = response.info().get_content_type()
                    print(f"    ✅ 成功！响应 Content-Type: {content_type} (大小: {len(response.read())} 字节)")
                    print(f"    🌟 最终图片可用 URL 为:\n    {url_thumb}")
                    break
            except Exception as e:
                print(f"    ❌ 失败: {e}")
    else:
        print("\n⚠️ 未能获取到任何照片 ID，跳过缩略图接口测试。")

if __name__ == "__main__":
    test_api()
