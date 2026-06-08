import os

def search_dir(d, queries):
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith(('.html', '.py', '.js')):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        for idx, line in enumerate(file):
                            for q in queries:
                                if q.lower() in line.lower():
                                    print(f"{path}:{idx+1}: {line.strip()[:150]}")
                                    break
                except Exception as e:
                    pass

search_dir(r"c:\Leo Harrison\Mia Analyst", ["mô hình", "phân tích", "hàng ngàn"])
