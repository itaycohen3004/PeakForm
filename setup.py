import os
import secrets
import string

def generate_secret(length=32):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for i in range(length))

def run_setup():
    print("[Setup] Starting PeakForm Setup...")
    
    env_path = ".env"
    example_path = ".env.example"
    
    # 1. Create .env if it doesn't exist
    if not os.path.exists(env_path):
        print(f"Creating {env_path} from {example_path}...")
        if not os.path.exists(example_path):
            print("[Error] .env.example not found!")
            return
            
        with open(example_path, "r") as f:
            content = f.read()
            
        # Generate a real random secret key
        new_secret = generate_secret()
        content = content.replace("SECRET_KEY=generate_me_locally", f"SECRET_KEY={new_secret}")
        
        with open(env_path, "w") as f:
            f.write(content)
        print(f"[Done] {env_path} created with a unique SECRET_KEY.")
    else:
        print(f"[Info] {env_path} already exists. Skipping creation.")

    # 2. Ensure directories exist
    os.makedirs("database", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    
    # 3. Final instructions
    print("\n[Done] PeakForm setup complete!")
    print("--------------------------------------------------")
    print("To run the application:")
    print("  python -m backend.app")
    print("--------------------------------------------------")
    print("Default Admin Credentials (from .env):")
    print("  Email: admin@peakform.app")
    print("  Pass:  Admin@1234")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_setup()

"""
English Summary:
This is a one-time utility script used to initialize the application environment. It copies 
the example environment file to generate a new '.env' file with a cryptographically secure, 
randomized SECRET_KEY. It also creates required directories for database and uploads storage.

סיכום בעברית:
קובץ זה נועד לרוץ רק פעם אחת, ממש אחרי שמתקינים את הפרויקט. התפקיד שלו הוא להכין את סביבת
העבודה: ליצור תיקיות שחסרות (כמו תיקיית העלאות ותמונות), ובעיקר - לייצר סיסמת אבטחה סודית ואקראית 
לחלוטין שבה המערכת תשתמש.
"""
