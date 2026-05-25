import os

def search_text(directory, target_text):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        if target_text in f.read():
                            print(f"Found in {path}")
                except Exception as e:
                    pass

search_text(r'C:\Leo Harrison\Mia Analyst\templates', 'correlation between user')
