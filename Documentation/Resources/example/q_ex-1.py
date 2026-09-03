#! /usr/bin/env python3
#
# A tiny simulator for a single queue.
# - richard.m.veras@ou.edu
#

# id, arrival time, service time
jobs = [("a",1,2),
        ("b",2,1),
        ("c",3,2),
        ("d",8,2),
        ("e",8,3),
        ("f",9,2)]

# |0 |1 |2 |3 |4 |5 |6 |7 |8 |9 |10|11|12
#     Ax_x_|
#           Bx|
#              Cx_x_|
#                          Dx|

clock=0
limit=20

work_queue=list()
jobs_complete=list()
job_in_service=None
service_time_left=0

while clock < limit:
    # 0. If a job is being serviced, decrement its time
    if job_in_service != None:
        service_time_left -= 1
        print("{c}: {j} has {t} time left".format(c=clock,j=job_in_service, t=service_time_left));

    # 1. If job is done then remove it
    if job_in_service != None and service_time_left == 0:
        print("{c}: {j} complete".format(c=clock,j=job_in_service));
        jobs_complete.append((job_in_service,clock,0))
        job_in_service = None

    # 2. Add new jobs in queue
    while len(jobs) and jobs[0][1] == clock:
        j = jobs.pop(0)
        work_queue.append(j)
        print("{c}: {j} added to queue".format(c=clock,j=j));
        
    # 1. If no job is being serviced, then add a job
    if job_in_service == None and len(work_queue)>0:
        j = work_queue.pop(0)
        job_in_service = j[0]
        service_time_left = j[2]
        print("{c}: {j} in service".format(c=clock,j=j));        
        
    print(''.join(["[{id}]".format(id=j[0]) for j in work_queue] + ["({id})->".format(id=job_in_service)]))
        
    #
    clock+=1

print(jobs_complete)


