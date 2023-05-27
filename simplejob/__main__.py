# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
# MIT License
from simplejob.simplejob import SimpleJobManager
import argparse
import json

parser = argparse.ArgumentParser(prog="simplejob", description="Simple Batch job executor")
parser.add_argument("jobContexts", type=str, help="Path to JSON file written job contexts.")
parser.add_argument("--logOutputDirectory", type=str, default=None, help="Path to directory for log file output.")
parser.add_argument("--loopInterval", type=float, default=1.0, help="Loop interval for job runner(seconds).")
args = parser.parse_args()

jobManager = SimpleJobManager(args.logOutputDirectory)
jobManager.entryFromJson(args.jobContexts)
try:
    jobManager.run(args.loopInterval)
except:
    pass

print(jobManager.report())
exit(1 if jobManager.errorOccurred() else 0)
