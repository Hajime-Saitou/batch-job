# simple-job
This is simple job execution module.

# Overview
You can execute job with relationship using this module. Job execution time can be delayed until other jobs are finished.

# Getting Started

## Run with the JobManager class

If you want to run a related many jobs, use the JobManager class.

At first, import the JobManager from this module.

```
from job import JobManager
```

Prepare a job context consisting of job id, command line, waiting list of other jobs, and pass it to as an argument to JobManager.entry().

```
jobContexts = [
    { "id": "hoge", "commandLine": r"timeout /t 1 /nobreak" },
    { "id": "piyo", "commandLine": r"timeout /t 3 /nobreak", "waiting": [ "hoge" ] },
    { "id": "fuga", "commandLine": r"timeout /t 5 /nobreak", "waiting": [ "hoge" ] },
    { "id": "moga", "commandLine": r"timeout /t 2 /nobreak", "waiting": [ "hoge", "fuga" ] },
]
jobManager = JobManager()
jobManager.entry(jobContexts)
```

Run all jobs through JobManager.runAllReadyJobs() until all jobs are finished or an error occurs. If necessary, call an interval timer in the loop. The example calls a 1 second interval timer.
Python's thread can not reentrantlly. Therefore you need re-call the JobManager.entry() with job contexts.

```
while not jobManager.completed():
    jobManager.runAllReadyJobs()
    if jobManager.errorOccurred():
        print("error occurred")
        break

    time.sleep(1)
```

When referencing the results of an all jobs, wait until an all running jobs finished.

```
jobManager.join()

for job in jobManager.jobs:
    print(job.id, job.exitCode, job.runningStatus)
```

## Run with the Job class

If you want to run a single job, use the Job class. A job class is a wrapping of a threading.Thread class.

At first, import the Job from this module.

```
from job import Job
```

Prepare a job context consisting of job id(optional), command line, waiting list of other jobs(do not set), and pass it to as an argument to Job.entry().

```
job = Job()
job.entry(commandLine="timeout /t 3 /nobreak")
```

When referencing the results of a job, wait until an all running jobs finished.

```
job.join()

print(job.exitCode)
```

## Output the job log

To output logs, specify the logOutputDirectory parameter to constructor of JobManager class or Job.entry(). The log file name is the job id with a "log" extension; if the job id is not specified, the base name from the first argument on the command line is used.

## Report
You can output the execution result as a report by calling report(). Returns an empty result for jobs that have not run.

Example for JobManager

```
{
    "results": [
        {
            "hoge": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "startDateTime": "2023/05/14 22:07:24.094654",
                "finishDateTime": "2023/05/14 22:07:25.214075",
                "elapsedTime": "00:00:01.119421"
            }
        },
        {
            "piyo": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "startDateTime": "2023/05/14 22:07:26.101694",
                "finishDateTime": "2023/05/14 22:07:29.213686",
                "elapsedTime": "00:00:03.111991"
            }
        },
        {
            "fuga": {
                "runnigStatus": "Completed",
                "exitCode": 1,
                "startDateTime": "2023/05/14 22:07:26.101694",
                "finishDateTime": "2023/05/14 22:07:26.133045",
                "elapsedTime": "00:00:00.31350"
            }
        },
        {
            "moga": {
                "runnigStatus": "Ready",
                "exitCode": "",
                "startDateTime": "",
                "finishDateTime": "",
                "elapsedTime": ""
            }
        }
    ]
}
```

Example for Job

```
{
    "runnigStatus": "Completed",
    "exitCode": 0,
    "startDateTime": "2023/05/14 22:07:30.145604",
    "finishDateTime": "2023/05/14 22:07:33.109779",
    "elapsedTime": "00:00:02.964175"
}
```
