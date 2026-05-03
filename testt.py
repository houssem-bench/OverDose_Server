import sys
import cv2

try:
    from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol
    pyzbar_ok = True
except Exception as exc:
    pyzbar_ok = False
    pyzbar_err = exc

print("OpenCV:", cv2.__version__)
print("has barcode_BarcodeDetector:", hasattr(cv2, "barcode_BarcodeDetector"))
print("has QRCodeDetector:", hasattr(cv2, "QRCodeDetector"))
print("pyzbar:", "OK" if pyzbar_ok else f"ERROR: {pyzbar_err}")

if len(sys.argv) < 2:
    print("\nUsage: python barcode_check.py path/to/image.jpg")
    sys.exit(1)

path = sys.argv[1]
img = cv2.imread(path)
if img is None:
    print("Image read failed:", path)
    sys.exit(1)

# OpenCV barcode detector
if hasattr(cv2, "barcode_BarcodeDetector"):
    det = cv2.barcode_BarcodeDetector()
    ok, decoded_info, decoded_types, _ = det.detectAndDecode(img)
    print("OpenCV barcode:", ok, decoded_info, decoded_types)
else:
    print("OpenCV barcode detector not available")

# OpenCV QR detector
qr = cv2.QRCodeDetector()
decoded, _, _ = qr.detectAndDecode(img)
print("OpenCV QR:", decoded)

# pyzbar decode
if pyzbar_ok:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    symbols = [
        ZBarSymbol.EAN13,
        ZBarSymbol.EAN8,
        ZBarSymbol.UPCA,
        ZBarSymbol.UPCE,
        ZBarSymbol.QRCODE,
        ZBarSymbol.CODE128,
        ZBarSymbol.CODE39,
        ZBarSymbol.I25,
    ]
    items = zbar_decode(gray, symbols=symbols)
    print("pyzbar:", [(i.type, i.data.decode("utf-8", errors="ignore")) for i in items])