# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
# MIT License
from simplejob.simplejob import SimpleJobManager

if __name__ == "__main__":
    # Run with the JobManager class
    jobManager = SimpleJobManager()
    jobManager.entryFromJson(r".\jobContexts.json")
    jobManager.run()

    print(jobManager.report())
