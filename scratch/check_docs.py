import os

def check_files():
    workspace = r"d:\PeakForm"
    missing_docs = []
    
    for root, dirs, files in os.walk(workspace):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or "venv" in root:
            continue
            
        for file in files:
            if file.endswith(".py") or file.endswith(".js"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    if "English Summary:" not in content or "סיכום בעברית:" not in content:
                        missing_docs.append(filepath)
                except Exception as e:
                    pass
                    
    for missing in missing_docs:
        print(missing)

if __name__ == "__main__":
    check_files()
