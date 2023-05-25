# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
# MIT License
from simplejob.simplejob import SimpleJobManager
import json

if __name__ == "__main__":
    # Run with the JobManager class
    jobContexts = [
        { "id": "hoge", "commandLine": r"timeout /t 1 /nobreak" },
        { "id": "piyo", "commandLine": r"timeout /t 3 /nobreak", "waits": [ "hoge" ] },
        { "id": "fuga", "commandLine": r"timeout /t 1 /nobreak", "waits": [ "hoge" ] },
        { "id": "moga", "commandLine": r"timeout /t 2 /nobreak", "waits": [ "piyo", "fuga" ] },
    ]
    jobManager = SimpleJobManager()
    jobManager.entry(jobContexts)
    jobManager.wait()

    print(json.dumps(jobManager.report(), indent=4))
