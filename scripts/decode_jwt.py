import sys
import jwt

def decode(token):
    try:
        # Don't verify signature, just read claims
        decoded = jwt.decode(token, options={"verify_signature": False})
        for k, v in decoded.items():
            print(f"{k}: {v}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        decode(sys.argv[1])
    else:
        print("Provide token as argument")
