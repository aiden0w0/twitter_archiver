from os import path, mkdir, chdir
from threading import Thread
from queue import Queue
import json

from account import Account
from api import TwitterAPI
from media_scheduler import MediaInfo, MediaScheduler, MediaType

# Numbers of downloading threads concurrently
THREADS = 3

class ArchiveWorker(Thread):
    def __init__(self, queue: Queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        # let's create an api instance for each thread
        config = {}
        with open('config.json', 'r') as f:
            config_file = f.read()
            config = json.loads(config_file)
        api = TwitterAPI(config["graphql_userbyscreenname_endpoint"], config["graphql_usertweets_endpoint"], config["graphql_tweetdetail_endpoint"], config["bearer_token"])
        if not api.get_guest_token():
            print('[!] failed to retrive guest token')
            self.queue.task_done()
        else:
            while True:
                site = self.queue.get()
                Account(site, api).archive()
                self.queue.task_done()

class ArchiveScheduler(object):
    def __init__(self):
        self.queue = Queue()

    def add_sites(self, sites: list):
        for site in sites:
            self.queue.put(site)

    def start_workers(self, threads: int):
        for _ in range(threads):
            worker = ArchiveWorker(self.queue)
            worker.daemon = True
            worker.start()

# borrowed from dixudx/tumblr-crawler
def parse_sites(filename : str) -> list:
    with open(filename, "r") as f:
        raw_sites = f.read().rstrip().lstrip()

    raw_sites = raw_sites.replace("\t", ",") \
                         .replace("\r", ",") \
                         .replace("\n", ",") \
                         .replace(" ", ",")
    raw_sites = raw_sites.split(",")

    sites = []
    for raw_site in raw_sites:
        site = raw_site.lstrip().rstrip()
        if site:
            sites.append(site)

    cleaned_sites = list(set(sites))
    cleaned_sites.sort()
    with open(filename, 'w') as outfile:
        for s in cleaned_sites:
            outfile.write(s + '\n')

    print('[.] input sites %d, after clean %d' % (len(sites), len(cleaned_sites)))

    return cleaned_sites
    
if __name__ == "__main__":
    cur_dir = path.dirname(path.realpath(__file__))
    sites: list = []

    filename = path.join(cur_dir, "sites.txt")
    if path.exists(filename):
        sites = parse_sites(filename)
        print('[.] processing %d sites' % len(sites))

    # check for data dir
    if not path.exists("data"):
        mkdir("data")
    
    if sites:
        a = ArchiveScheduler()
        a.start_workers(THREADS)
        a.add_sites(sites)
        a.queue.join()

    print('[√] archive finished')