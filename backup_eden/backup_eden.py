# Python v3.11.6

import asyncio
import argparse

import aiohttp
import aiofiles

from os import mkdir, makedirs
from os.path import isdir
from shutil import rmtree
from urllib.parse import urlparse, unquote

from bs4 import BeautifulSoup


class Main:
    def __init__(self, base_url, nr_workers):
        self.base_url = base_url
        self.nr_workers = nr_workers
        self.seen = set()
        self.visited = set()

        self.work_q = asyncio.Queue()
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "backup-edenbox/0.1"}
        )


    async def run(self):
        base_dir = urlparse(self.base_url).netloc
        if isdir(base_dir):
            while True:
                opt = input(
                    f'A directory for {base_dir} already exists, do you wish to override it? [y/N] ')
                if opt.lower() in ["n", "N"]:
                    await self.shut_down()
                    return
                elif opt.lower() in ["y", "Y"]:
                    rmtree(base_dir)
                    break
                else:
                    continue

        await self._run()


    async def _run(self):
        workers = [asyncio.create_task(self.do_work())
                   for _ in range(self.nr_workers)]

        await self.work_q.put(self.base_url + "/")

        try:
            await self.work_q.join()
        except KeyboardInterrupt:
            pass

        for task in workers:
            task.cancel()

        for tasks in workers:
            await task

        await self.shut_down()


    async def do_work(self):
        try:
            while True:
                new_url = await self.work_q.get()
                self.visited.add(new_url)
                try:
                    async with self.session.get(new_url) as response:
                        if response.status != 200:
                            print(
                                f'Failed request to {new_url}, status {response.status}')
                            self.work_q.task_done()
                            continue

                        parsed_url = urlparse(new_url)
                        path = parsed_url.netloc + parsed_url.path

                        content_type = response.headers.get('content-type')
                        if content_type is None or 'text/html' not in content_type:
                            await self.save_content(path, content=response)
                        else:
                            makedirs(unquote(path))
                            await self.traverse(path, html=await response.text())

                        self.work_q.task_done()

                except aiohttp.ClientConnectionError as e:
                    print(f'Connection error', str(e))
                    self.work_q.task_done()
                except asyncio.CancelledError:
                    return
                except Exception as e:
                    print(repr(e))
                    self.work_q.task_done()

        except asyncio.CancelledError:
            return


    async def traverse(self, path: str, html: str):
        bs = BeautifulSoup(html, 'html.parser')

        anchors = bs.find_all('a', href=True)
        if anchors is None:
            return

        for anchor in anchors:
            ref = anchor['href']
            if ref == '':
                continue

            if ref[0] != '.' or ref[0:2] == '..':
                continue

            new_url = 'https://' + path + ref[2:]

            if not {new_url} - self.visited - self.seen:
                continue

            self.seen.add(new_url)
            await self.work_q.put(new_url)

        return


    async def save_content(self, path: str, content: aiohttp.ClientResponse):
        async with aiofiles.open(unquote(path), 'wb') as fp:
            await fp.write(await content.read())
            print(f'Saved {path}')


    async def shut_down(self):
        await self.session.close()


async def entry_coro(dir_url: str, nr_workers: int):
    await Main(base_url=dir_url, nr_workers=nr_workers).run()


def main():
    parser = argparse.ArgumentParser(
        prog='dleden',
        description='Program that backups a very specific HTTP file serving service'
    )

    parser.add_argument(
        'url', help='The url of the base dir or any sub directory')
    parser.add_argument('--nr-workers', default=30,
                        help='Number of max concurrent requests permitted (default: 30)')

    args = parser.parse_args()

    if args.url[len(args.url) - 1] == '/':
        args.url = args.url[:-1]

    asyncio.run(entry_coro(args.url, args.nr_workers))


if __name__ == '__main__':
    main()
