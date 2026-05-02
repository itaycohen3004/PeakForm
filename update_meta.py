import os
import glob

directory = r'd:\PeakForm\frontend\pages'
html_files = glob.glob(os.path.join(directory, '*.html'))

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_meta1 = '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
    old_meta2 = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    new_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    
    content = content.replace(old_meta1, new_meta).replace(old_meta2, new_meta)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Updated {len(html_files)} files.")

"""
English Summary:
A small maintenance script that performs bulk string replacements across all HTML files in the 
frontend directory. Used primarily to enforce standardized viewport meta tags for optimal mobile rendering.

סיכום בעברית:
סקריפט עזר פשוט שרץ על כל קבצי התצוגה (HTML) של האתר ומתקן להם את הגדרות התצוגה, 
כדי להבטיח שהאתר ייראה מצוין גם בטלפונים ניידים ושהמסך לא "יקפוץ" כשלוחצים על כפתורים.
"""
