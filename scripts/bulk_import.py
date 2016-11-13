# -*- coding: utf-8 -*-
# -*- mode: python -*-

import json
import requests as rq

if __name__=="__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("endpoint", help="URL to POST records to")
    p.add_argument("records", help="file with records as JSON array")

    args = p.parse_args()

    data = json.load(open(args.records, 'r'))
    for record in data:
        print(record)
        r = rq.post(args.endpoint, json=record)
        print(r.status_code)
