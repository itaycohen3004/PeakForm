# כל הספריות האלו מגיעות מחבילה שנקראת "cryptography" שעוזרת לנו לעשות דברים סודיים (הצפנה)
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

# פונקציה לייצור תעודת אבטחה שמאפשרת לנו להצפין נתונים בין השרת ללקוח
def generate_self_signed_cert(certfile="cert.pem", keyfile="key.pem"):
    print("Generating RSA key... (מייצר מפתח סודי ענק ואקראי)")
    # אנחנו מייצרים כאן מפתח סודי (כמו סיסמה מאוד ארוכה שאי אפשר לנחש)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048, # גודל המפתח, ככל שגדול יותר - ככה בטוח יותר
    )
    
    # מידע שיירשם בתעודה: של מי האתר הזה? מאיזו מדינה?
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Secure Server Inc"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"), # רץ במחשב שלנו
    ])
    
    print("Generating Self-Signed Certificate... (מייצר תעודת אבטחה שלנו)")
    # בונים את התעודה, מכניסים בה את השם שלנו ואת המפתח שלנו
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key() # המפתח הפומבי (שאותו נותנים לכולם כדי שיצפינו אלינו דברים)
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow() # תקף החל מעכשיו
    ).not_valid_after(
        # התעודה תהיה בתוקף למשך 10 ימים, ואז צריך להכין חדשה! (בשביל בטיחות)
        datetime.datetime.utcnow() + datetime.timedelta(days=10)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    ).sign(private_key, hashes.SHA256()) # חותמים על התעודה שלא יוכלו לזייף אותה
    
    print(f"Writing {certfile} and {keyfile}... (שומר הכל לקבצים במחשב)")
    
    # שומר את התעודה הפומבית
    with open(certfile, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
        
    # שומר את המפתח הסודי (אותו חייב לשמור בסוד!)
    with open(keyfile, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print("Done! (סיימנו!)")

if __name__ == "__main__":
    generate_self_signed_cert()

"""
English Summary:
This script acts as our local Certificate Authority (CA). It utilizes the 'cryptography' library 
to programmatically generate an asymmetric 2048-bit RSA key pair. It then builds and signs an X.509 
TLS certificate valid for 10 days, saving both the public certificate and private key to disk 
for the server to use during SSL handshakes.

סיכום בעברית:
קובץ זה מייצר בשבילנו תעודת אבטחה דיגיטלית - כמו תעודת זהות של שרת שמאפשרת תקשורת מאובטחת.
הוא מייצר 2 קבצים: המפתח הפרטי (הסודי שאסור לגלות לאף אחד) והתעודה הפומבית. 
כשהשרת שלנו משתמש בקבצים האלו, הוא יוצר מנהרה מוצפנת ומסווגת כך שגם אם מישהו יאזין 
לטלפון או לראוטר בבית - הוא יראה רק ג'יבריש! התעודה פג תוקף לאחר 10 ימים מטעמי ביטחון.
"""
