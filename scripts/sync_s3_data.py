"""Placeholder utility for syncing S3 meeting payloads locally."""
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--bucket', required=True)
parser.add_argument('--prefix', default='')
parser.add_argument('--dest', default='data')
args = parser.parse_args()

cmd = ['aws', 's3', 'sync', f"s3://{args.bucket}/{args.prefix}", args.dest]
subprocess.run(cmd, check=True)
