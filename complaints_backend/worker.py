#!/usr/bin/env python
"""
Background worker for processing notification and maintenance jobs
Run with: python worker.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from redis import Redis
from rq import Worker, Queue, Connection

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

if __name__ == '__main__':
    try:
        redis_conn = Redis.from_url(redis_url)
        redis_conn.ping()
        
        with Connection(redis_conn):
            queues = ['notifications', 'maintenance']
            worker = Worker(queues)
            
            print(f'Starting RQ worker for queues: {", ".join(queues)}')
            print(f'Redis URL: {redis_url}')
            
            worker.work()
            
    except Exception as e:
        print(f'Failed to start worker: {str(e)}')
        print('Make sure Redis is running and REDIS_URL is configured correctly')
        sys.exit(1)
