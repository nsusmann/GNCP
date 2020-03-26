############################################
'''

4/27/2018

Compute a viewshed with parallel processing using GRASS 7.4. and Python 2.7
Configured for use in a batch computation scenario with multiple cores per batch.

B. Gregor
bgregor@bu.edu
Research Computing Services
Boston University



'''
############################################


import grass.script as gscript
import grass.script.setup as gsetup
from grass.pygrass.modules import Module, ParallelModuleQueue

import sys
import os
import copy
import time
import argparse


class ParallelViewPoints:
    # some values
    # atmospheric refraction coefficient
    REFRACTION_COEF = 0.13
    # Max memory per calculation
    MEM_MBYTES = 8000
    # Observer height
    OBS_ELEVATION = 1.65

    def __init__(self, viewpoints_file, elevation_file, output_file, njobs, job_index, ncores):
        # Store parameters
        self.viewpoints_file = viewpoints_file
        self.elevation_file = elevation_file
        self.output_file = output_file
        self.njobs = njobs
        self.job_index = job_index
        self.ncores = ncores
        self.print_now('ParallelViewPoints: parameters stored')
        
        self.output_name=os.path.basename(self.output_file)
        self.viewpoints_name = os.path.splitext(os.path.basename(self.viewpoints_file))[0]
        self.elevation_name = os.path.splitext(os.path.basename(self.elevation_file))[0]
        self.print_now('ParallelViewPoints: names stored')

        # Open the viewpoints file in GRASS
        gscript.run_command('v.import', input=self.viewpoints_file,
                        output=self.viewpoints_name,
                        extent='input', overwrite=1)

        self.print_now('ParallelViewPoints: Viewpoints loaded into GRASS.')
        # Create the master pointlist
        # Get the points from the point file into Python
        output_points = gscript.read_command("v.out.ascii", flags='r', input=self.viewpoints_name, type="point",
                                             format="point", separator=",").strip()
        self.all_points = []
        for line in output_points.splitlines():
            if line:  # see ticket #3155
                self.all_points.append(line.strip().split(','))

        self.print_now('ParallelViewPoints: Viewpoints loaded into Python')

        # load the elevation map
        try:
            gscript.run_command('g.remove',type='raster',name=self.elevation_name,flags='f')
        except Exception as e:
            print('remove error: %s' % e)
        gscript.run_command('r.in.gdal',input=self.elevation_file,output=self.elevation_name)
        # Set the compute region
        gscript.run_command('g.region',flags='p',raster=self.elevation_name)

        self.print_now('ParallelViewPoints: elevation map loaded. Ready to calculate.')

    def calc_viewpoints(self):
        ''' Calculate the output viewpoints map. '''

        # Get the set of points this job will work on
        points = self.get_viewpoints_subset()

        # Process them in parallel
        vshed_list = self.parallel_process(points)

        # Create the output file
        self.create_output_file(vshed_list)


    def get_viewpoints_subset(self):
        # Based on the job count and index, compute the number of points
        # for all possible jobs.  Then select the # for this job and return
        # the subset list containing those points.
        num_pts = len(self.all_points)
        # Compute the number of points per job.
        pts_per_job = num_pts / self.njobs
        # Make a list of the pts_per_job for each job
        job_lst = [pts_per_job] * self.njobs
        # Loop through the integer remainder and distribute them
        for pt in xrange(num_pts % self.njobs):
            job_lst[pt % len(job_lst)] += 1
        # Now get the number this one will do
        this_job_count = job_lst[self.job_index]
        # Sum the preceding point counts to get the starting index
        start_index = sum(job_lst[0:self.job_index])
        # Return the subset
        return self.all_points[start_index:start_index + this_job_count]

    def parallel_process(self,points):
        # Run the viewshed for a few points
        vshed_list = []
        # Set up a processing queue
        queue = ParallelModuleQueue(nprocs=self.ncores)

        # Create a PyGRASS Module to run the viewshed calc
        viewshed_calc = Module('r.viewshed', overwrite=True, run_=False,
                               observer_elevation=self.OBS_ELEVATION,
                               memory=self.MEM_MBYTES,
                               refraction_coeff=self.REFRACTION_COEF,
                               input=self.elevation_name,
                               quiet=True)
        stime = time.time()
        gscript.message('Queueing %s viewpoint calculations...' % len(points))
        for site in points:
            ptname = site[2]
            tmpdir = os.path.join(os.environ['TMPDIR'], 'viewshed_%s' % ptname)
            if not os.path.exists(tmpdir):
                os.makedirs(tmpdir)
            # gscript.verbose(_('Calculating viewshed for location %s,%s (point name = %s)') % (site[0], site[1], ptname))
            tempry = "vshed_%s" % ptname
            vshed_list.append(tempry)
            new_viewshed_calc = copy.deepcopy(viewshed_calc)
            vs = new_viewshed_calc(output=tempry, coordinates=(site[0], site[1]), directory=tmpdir)
            queue.put(vs)
        queue.wait()
        etime = time.time()
        self.print_timing(stime,etime,len(points))
        return vshed_list

    def print_timing(self,stime,etime,npts):
        # Total time
        dt = etime - stime
        # Avg time per point
        avg_time = dt / npts * self.ncores
        gscript.message('Elapsed processing time for %s points: %s' % (dt,npts))
        gscript.message('Average time per point: %s' % avg_time)


    def create_output_file(self, vshed_list):
        # Add our job index to the output file
        ofile = self.output_file + '_' + str(self.job_index + 1) + '.grd'
        stime = time.time()
        gscript.message('Calculating "Cumulative Viewshed" map.')

        gscript.run_command("r.series", verbose=True, overwrite=1,
                            input=','.join(vshed_list), output=self.output_name, method="count")
        gscript.message("Removing temporary viewshed maps")
        gscript.run_command("g.remove", quiet=False, flags='f', type='raster', name=",".join(vshed_list))

        gscript.message("Exporting to output file in gTIFF format: %s" % ofile)
        gscript.run_command('r.out.gdal',input=self.output_name, output=ofile, format='AAIGrid',verbose=True)

        etime = time.time()
        gscript.message('Elapsed processing time: %s  Time per pt: %s' % (etime - stime, (etime - stime) / len(vshed_list)))

    def print_now(self,msg):
        sys.stdout.write('%s\n' % msg)
        sys.stdout.flush()

def check_file(testfile):
    if not os.path.exists(args.viewpoints):
        sys.stderr('File not found: %s' % testfile)
        exit(1)

if __name__ == '__main__':
    # Set up arguments.
    # GRASS stuff is loaded from environment variables GISDBASE,LOCATION_NAME,MAPSET,GISBASE
    # shape file, elevation map, and output gTIFF filename is loaded from command line
    # Total number of processes, this process's index (from 1), and number of procs to use
    # are also loaded from the command line.

    # Create the command line parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-viewpoints',help='Full path to the file containing viewpoints')
    parser.add_argument('-elevations',help='Full path to the elevation map')
    parser.add_argument('-output_file',help='Full path to an output filename in gTIFF format.')
    parser.add_argument('-njobs', type=int, help='Number of jobs processing the viewpoints file.')
    parser.add_argument('-job_index', type=int, help='Index (counted from 1) of this job')
    parser.add_argument('-ncores',type=int, help='Number of cores to use for parallel computations')
    args = parser.parse_args()

    # Set some defaults
    ncores = 1
    njobs = 1
    job_index = 0
    if args.ncores:
        ncores = args.ncores
    if args.njobs:
        njobs = args.njobs
    if args.job_index:
        job_index = args.job_index - 1
    print("This is job %s out of %s.  Processing with %s cores." % (job_index+1, njobs, ncores))
    sys.stdout.flush()
    # Do the input files exist?
    check_file(args.viewpoints)
    check_file(args.elevations)
    # Make the output directory if needed
    try:
        os.makedirs(os.path.dirname(args.output_file))
    except:
        pass

    # Retrieve some GRASS info
    base_dir = os.environ['GISDBASE']
    location_name = os.environ['LOCATION_NAME']
    mapset = os.environ['MAPSET']
    gisbase = os.environ['GISBASE']

    # Set up GRASS using the available environment variables
    print('Initializing GRASS')
    sys.stdout.flush()

    gsetup.init(gisbase, base_dir, location_name, mapset)

    # Create the GRASS parallel viewshed object
    print('Setting up viewpoints calculation.')
    sys.stdout.flush()
    cv = ParallelViewPoints(args.viewpoints, args.elevations, args.output_file, njobs, job_index, ncores)

    # Run the calculation
    cv.calc_viewpoints()
