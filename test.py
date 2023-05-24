# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
# MIT License
import time
from simplejob.simplejob import SimpleJobManager, SimpleJob
import json

if __name__ == "__main__":
    # Run with the JobManager class
    jobContexts = [
        { "id": "hoge", "commandLine": r"timeout /t 1 /nobreak" },
        { "id": "piyo", "commandLine": r"timeout /t 3 /nobreak", "waits": [ "hoge" ] },
        { "id": "fuga", "commandLine": r"timeout /z", "waits": [ "hoge" ] },
        { "id": "moga", "commandLine": r"timeout /t 2 /nobreak", "waits": [ "hoge", "fuga" ] },
    ]
    jobManager = SimpleJobManager()
    jobManager.entry(jobContexts)

    while not jobManager.completed():
        jobManager.runAllReadyJobs()
        if jobManager.errorOccurred():
            print("error occurred")
            break

        time.sleep(1)

    jobManager.join()

    print(json.dumps(jobManager.report(), indent=4))

    # Run with the Job class
    job = SimpleJob()
    job.entry(commandLine="timeout /t 3 /nobreak")
    job.start()

    job.join()

    print(json.dumps(job.report(), indent=4))
