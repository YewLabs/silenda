#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import hashlib
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'silenda.settings.' + os.environ.setdefault('DJANGO_ENV', 'dev'))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    if 'DJANGO_ENV' in os.environ and 'SILENDA_PROD_AUTHED' not in os.environ:
        if os.environ['DJANGO_ENV'] == 'prod' or os.environ['DJANGO_ENV'].startswith('gae'):
            secretCode = input('>').strip()
            # yolo
            if hashlib.sha256(secretCode.encode('utf-8')).hexdigest() != '311fe3feed16b9cd8df0f8b1517be5cb86048707df4889ba8dc37d4d68866d02':
                print("You probably shouldn't be using this environment.")
                sys.exit(1)
            else:
                os.environ['SILENDA_PROD_AUTHED'] = '1'
    main()
