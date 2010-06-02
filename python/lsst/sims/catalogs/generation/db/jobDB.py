#!/usr/bin/env python
from dbModel import *
from sqlalchemy import func
import datetime as dt
from pytz import timezone
import socket

class LogEvents(object):
  def __init__(self, jobdescription="", ip = None):
    setup_all()
    create_all()
    self._tasknumber = None
    self._jobid = None
    jobid = b_session.query(func.max(CatalogEventLog.jobid)).one()[0]
    print "my Jobid is",jobid
    if jobid is None:
      self._jobid = 1
    else:
      self._jobid = jobid + 1
    self._jobdescription = jobdescription
    if ip is None:
      self._ip = socket.gethostbyname(socket.gethostname())
    else:
      self._ip = ip

  def persist(self, key, value, description):
    print "Persisting Task number %s"%(str(self._tasknumber))
    CatalogEventLog(jobid=self._jobid, pkey=unicode(key),
            pvalue=unicode(value),
            time=dt.datetime(1,1,1).now(timezone('US/Pacific')),
            taskNumber=self._tasknumber, ip=self._ip,
            description=unicode(description))
    b_session.commit()

  def registerTaskStart(self, tasknumber=None):
    key = "TASK_START" 
    if tasknumber is None:
      tasknumber = b_session.query(func.max(CatalogEventLog.taskNumber)).one()[0]
      print "Task number %s"%(str(tasknumber))
      if tasknumber is None:
        tasknumber = 1
    else:
      pass
    self._tasknumber = tasknumber
    print "Task number %s"%(str(self._tasknumber))
    value = "Task started"
    self.persist(key, value, self._jobdescription)
    
  def registerEvent(self, eventid, eventdescription=""):
    key = "TASK_EVENT"
    value = eventid
    self.persist(key, value, eventdescription)

  def registerTaskStop(self, exitvalue=1):
    key = "TASK_STOP"
    value = "Task number %s stopped with term value %s"%(str(self._tasknumber), str(exitvalue))
    self.persist(key, value, self._jobdescription)

class JobState(object):
  def __init__(self, jobid=None):
    setup_all()
    self._jobid = None
    self._states = {}
    if jobid is None:
      jobid = b_session.query(func.max(JobStateLog.jobid)).one()[0]
      if jobid is None:
        self._jobid = 1
      else:
        self._jobid = jobid + 1
    else:
      try:
        jobid = int(jobid)
      except:
        raise Exception("The jobid could not be cast as an int")
      self._jobid = jobid
      statearr = JobStateLog.query.filter("jobid = %i"%jobid).all()
      for state in statearr:
        self._states[state.pkey] = state

  def getJobId(self):
    return self._jobid

  def updateState(self, key, state):
    if self._states.has_key(key):
      self._states[key].pvalue = unicode(state)
      self._states[key].time = dt.datetime(1,1,1).now(timezone('US/Pacific'))
      b_session.commit()
    else:
      self._states[key] = JobStateLog(jobid=self._jobid, pkey=unicode(key),
              pvalue=unicode(state),
              time=dt.datetime(1,1,1).now(timezone('US/Pacific')))
      b_session.commit()
  def queryState(self, key):
    if self._states.has_key(key):
      b_session.refresh(self._states[key])
      return self._states[key].pvalue
    else:
      return None

  def showStates(self):
    for k in self._states.keys():
      b_session.refresh(self._states[k])
      print k, self._states[k].pvalue