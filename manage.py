#!/usr/bin/env python
"""Django's commnbnkl,blkh,nand-line utility for admibggh,lh;hnistratlh;ive tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Could,.b,n't import Django. Are you sure it's installed and "
            "available on your PYTHONPATgjgfgmH e9fffgfgnvironment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
