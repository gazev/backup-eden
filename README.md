## Installation
```
git clone https://github.com/gazev/backup-eden
cd backup-eden
pip install .
```

## Usage
```
usage: dleden [-h] [--nr-workers NR_WORKERS] url

Program that backups a very specific HTTP file serving service

positional arguments:
  url                   The url of the base dir or a sub directory

options:
  -h, --help            show this help message and exit
  --nr-workers NR_WORKERS
                        Number of max concurrent requests permitted (default: 30)
```

