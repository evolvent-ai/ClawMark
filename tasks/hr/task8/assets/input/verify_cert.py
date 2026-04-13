#!/usr/bin/env python3
"""Task-local mock certificate verifier for Task 13."""
import sys


CERT_DB = {
    "PMP-88321": "Revoked",
    "PMP-10294": "Valid",
    "PMP-77120": "Valid",
    "PMP-66103": "Valid",
    "PMP-44082": "Valid",
}


def main():
    if len(sys.argv) != 2:
        print("Usage: verify_cert.py <certificate_id>")
        sys.exit(2)

    cert_id = sys.argv[1].strip()
    status = CERT_DB.get(cert_id, "Not Found")
    print(f"CERTIFICATE: {cert_id}")
    print(f"STATUS: {status}")
    sys.exit(0 if status != "Not Found" else 1)


if __name__ == "__main__":
    main()
