import argparse

from aiohttp import web

from . import config
from .server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="TopLocal Studio inference service")
    parser.add_argument("--port", type=int, default=config.PORT)
    args = parser.parse_args()
    print(f"localai-service listening on http://{config.HOST}:{args.port}", flush=True)
    web.run_app(create_app(), host=config.HOST, port=args.port, print=None)


if __name__ == "__main__":
    main()
