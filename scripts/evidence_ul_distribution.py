#!/usr/bin/env python

"""
The main purpose of this script is to assess the distribution of evidence ratios produced by 
lalapps_pulsar_parameter_estimation_nested when running on the same piece of data for different numbers of 
live points. It will also check the consistency of the evidence ratio with that produced through a grid-based 
trapezium rule numerical integration for the same data. It will finally look at the value of the 95% upper 
limit on signal amplitude and how that varies with the number of live points used.

It will perform these tests both the Student's t and Gaussian likelihood functions.

Copyright (C) 2015 Matthew Pitkin
"""

import os
import subprocess
import numpy as np
import uuid

# import some pulsar utilities
from lalapps import pulsarpputils as pppu

# the base directory
basedir = '/home/sismp2/projects/code_testing/evidence_ul_distribution'

# create a set of some fake noise
mu = 0. # mean
sigma = 1e-23 # standard deviation

fakedata = np.zeros((1440, 3))
fakedata[:,0] = np.arange(900000000., 900086400., 60) # GPS time stamps
fakedata[:,1:] = mu + sigma*np.random.randn(1440, 2)  # real and imaginary data

# output the data
datafile = os.path.join(basedir, 'data.txt.gz')
np.savetxt(datafile, fakedata, fmt='%.1f\t%.7e\t%.7e')

# create a prior file
priorfile = os.path.join(basedir, 'prior.txt')
fp = open(priorfile, 'w')
h0max = 1e-21 # maximum of h0 range
priortxt = """
H0 uniform 0 %.2e
COSIOTA uniform -1 1
PHI0 uniform 0 %.8f
PSI uniform 0 %.8f
""" % (h0max, np.pi, np.pi/2.)
fp.write(priortxt)
fp.close()

# create a par file
parfile = os.path.join(basedir, 'pulsar.par')
fp = open(parfile, 'w')
partxt = """
PSRJ J0000-0000
RAJ 00:00:00.0
DECJ 00:00:00.0
PEPOCH 55000.0
F0 100.0
"""
fp.write(partxt)
fp.close()

# set the numbers of live points to run with
nlives = [128, 256, 512, 1024, 2048, 4096]

# set the number of runs with each case
Nruns = 250

# create log directory if it doesn't exist
logdir = os.path.join(basedir, 'log')
if not os.path.isdir(logdir):
  os.mkdir(logdir)

# setup Condor sub file for runs
subfile = os.path.join(basedir, 'run.sub')
execu = os.path.join(os.environ['LSCSOFT_LOCATION'], 'bin/lalapps_pulsar_parameter_estimation_nested')
fp = open(subfile, 'w')
subfiletxt = """
universe = vanilla
executable = %s
arguments = " --prior-file %s --detectors H1 --par-file %s --Nmcmcinitial 200 --outfile $(macrooutfile) \
--Nlive $(macronlive) --gzip --non-fixed-only --input-files %s "
getenv = True
log = %s
error = %s
output = %s
notification = never
accouting_group = ligo.dev.s6.cw.targeted.bayesian
queue 1
""" % (execu, priorfile, parfile, datafile, os.path.join(logdir, '$(cluster).log'), \
       os.path.join(logdir,'$(cluster).err'), os.path.join(logdir,'$(cluster).out'))
fp.write(subfiletxt)
fp.close()

# create dag for all the jobs
dagfile = os.path.join(basedir, 'run.dag')
fp = open(dagfile, 'w')

for n in nlives:
  # create output directory
  livedir = os.path.join(basedir, '%d' % n)
  if not os.path.isdir(livedir):
    os.mkdir(livedir)
    
  for i in range(n):
    # create output file
    outfile = os.path.join(livedir, 'nest_%04d.txt' % i)
    
    # unique ID
    ui = uuid.uuid4().hex
    dagstr = 'JOB %s %s\nRETRY %s 0\nVARS %s macrooutfile=\"%s\" macronlive=\"%d\"\n' % (ui, subfile, ui, \
      ui, outfile, n)
    fp.write(dagstr)
    
fp.close()
