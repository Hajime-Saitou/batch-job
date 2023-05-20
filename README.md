# simplejob
This is simple job execution module.

# Overview
You can execute job with relationship using this module. Job execution time can be delayed until other jobs are finished.

# Getting Started

## Run with the JobManager class

If you want to run a related many jobs, use the JobManager class.

At first, import the JobManager from this module.

```
from simplejob import JobManager
```

Prepare a job context consisting of job parameters and pass it as an argument to JobManager.entry().

id ... Job ID (arbitrary name, if omitted, the base name of the first command line argument)
command line ... command to execute and command line parameters
Waiting list of other job IDs ... List of job IDs waiting to run

```
jobContexts = [
    { "id": "hoge", "commandLine": r"timeout /t 1 /nobreak" },
    { "id": "piyo", "commandLine": r"timeout /t 3 /nobreak", "waiting": [ "hoge" ] },
    { "id": "fuga", "commandLine": r"timeout /t 5 /nobreak", "waiting": [ "hoge" ] },
    { "id": "moga", "commandLine": r"timeout /t 2 /nobreak", "waiting": [ "hoge", "fuga" ] },
]
jobManager = SimpleJobManager()
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
from simplejob import SimpleJob
```

Prepare a job context consisting of job id(optional), command line, waiting list of other jobs(do not set), and pass it to as an argument to Job.entry().

```
job = SimpleJob()
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

Example for SimpleJobManager.report()

```
{
    "results": [
        {
            "hoge": {
                "runnigStatus": "Completed",
                "retried": null,
                "exitCode": 0,
                "startDateTime": "2023/05/18 21:45:24.243201",
                "finishDateTime": "2023/05/18 21:45:25.189776",
                "elapsedTime": "00:00:00.946575"
            }
        },
        {
            "piyo": {
                "runnigStatus": "Completed",
                "retried": null,
                "exitCode": 0,
                "startDateTime": "2023/05/18 21:45:25.253739",
                "finishDateTime": "2023/05/18 21:45:28.116363",
                "elapsedTime": "00:00:02.862623"
            }
        },
        {
            "fuga": {
                "runnigStatus": "Completed",
                "retried": null,
                "exitCode": 1,
                "startDateTime": "2023/05/18 21:45:25.253739",
                "finishDateTime": "2023/05/18 21:45:25.269691",
                "elapsedTime": "00:00:00.15952"
            }
        },
        {
            "moga": {
                "runnigStatus": "Ready",
                "retried": null,
                "exitCode": null,
                "startDateTime": null,
                "finishDateTime": null,
                "elapsedTime": null
            }
        }
    ]
}
```

Example for SimpleJob.report()

```
{
    "runnigStatus": "Completed",
    "retried": null,
    "exitCode": 0,
    "startDateTime": "2023/05/18 21:45:28.276206",
    "finishDateTime": "2023/05/18 21:45:31.197224",
    "elapsedTime": "00:00:02.921018"
}
```

## Retry on timed out
If the job fails by timed out, it can be retried. The retry parameters are as follows.Retry parameters can be set for individual jobs.

retry ... Retry count (default is 0, no retry)
timeout ... Number of seconds to timeout the job (default is None, no timeout)
delay ... number of seconds to delay the job on retry (default 0, no delay)
backkoff ... power to back off the retry interval (default 1)

The report for a failed retry is shown below.

```
{
    "runnigStatus": "RetryOut",
    "retried": 1,
    "exitCode": null,
    "startDateTime": "2023/05/18 21:47:38.528989",
    "finishDateTime": "2023/05/18 21:47:43.594701",
    "elapsedTime": "00:00:05.65712"
}
```
