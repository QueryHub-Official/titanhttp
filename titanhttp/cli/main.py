import sys
import argparse
from .commands import Commands


def main():
    parser = argparse.ArgumentParser(prog="titanhttp")
    sub = parser.add_subparsers(dest="cmd")

    get = sub.add_parser("get", help="HTTP GET")
    get.add_argument("url")
    get.add_argument("--output", "-o")

    post = sub.add_parser("post", help="HTTP POST")
    post.add_argument("url")
    post.add_argument("--json", "-j")
    post.add_argument("--form", "-f", nargs=2, action="append")

    dl = sub.add_parser("download", help="Download file")
    dl.add_argument("url")
    dl.add_argument("--output", "-o", required=True)
    dl.add_argument("--resume", action="store_true")

    args = parser.parse_args()
    Commands.run(args)


if __name__ == "__main__":
    main()
