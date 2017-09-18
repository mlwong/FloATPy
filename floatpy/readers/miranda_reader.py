import glob
import numpy

import matplotlib
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

from base_reader import BaseReader

class MirandaReader(BaseReader):
    """
    Class to read in parallel binary data generated by the Miranda code.
    """

    def __init__(self,plotmir_path):
        """
        Constructor of the Miranda reader class
        """
               
        # Main meta data file
        self.filename_prefix = plotmir_path
        self.plotMir = plotmir_path
        
        # Proc boundaries
        self.procExtents = {}

        self.periodic = periodic

        # Read in metadata and make a dictionary
        self.plotDict = {}
        pid = open(self.plotMir)
        lines = pid.readlines()
        for line in lines[1:]:
            if (":" in line):
                ikey = line.split(':')[0]
                data = line.split(':')[1].split('#')[0].strip()
                self.plotDict[ikey] = [data]
            else:
                data = line.split('#')[0].strip()
                self.plotDict[ikey].append(data)
                    
        # Unpack the dict into usable data
        self.verbose = verbose
        self.zonal = False
        self.legacy = False
        if self.plotDict.has_key('zonal'):
            if ( 'yes' in self.plotDict['zonal'] ):
                self.zonal = True
        else:
            if self.verbose:
                print "Warning: Zonal flag not given... using legacy options."
            self.legacy = True
            

        self.dx = float(filter(None,self.plotDict['spacing'][0].split(' '))[0].replace('D','e'))
        self.dy = float(filter(None,self.plotDict['spacing'][0].split(' '))[1].replace('D','e'))
        self.dz = float(filter(None,self.plotDict['spacing'][0].split(' '))[2].replace('D','e'))


        # These include the ghost points
        self.ax = int(filter(None,self.plotDict['blocksize'][0].split(' '))[0])
        self.ay = int(filter(None,self.plotDict['blocksize'][0].split(' '))[1])
        self.az = int(filter(None,self.plotDict['blocksize'][0].split(' '))[2])
 
        self.nx = int(filter(None,self.plotDict['domainsize'][0].split(' '))[0])
        self.ny = int(filter(None,self.plotDict['domainsize'][0].split(' '))[1])
        self.nz = int(filter(None,self.plotDict['domainsize'][0].split(' '))[2])

        self.px = self.nx / self.ax
        self.py = self.ny / self.ay
        self.pz = self.nz / self.az

        offsetx = 0
        offsety = 0
        offsetz = 0
        if self.zonal:
            if self.nx > 1:
                offsetx = 1
            if self.ny > 1:
                offsety = 1
            if self.nz > 1:
                offsetz = 1            

        self.xblk = 0
        self.yblk = 0
        self.zblk = 0
        
        if not self.legacy:


            if not self.zonal:
                if self.px > 1:
                    self.xblk = 1
                if self.py > 1:
                    self.yblk = 1
                if self.pz > 1:
                    self.zblk = 1

            # Fix the local indices
            self.ax -=  npy.minimum(self.px-1,1)
            self.ay -=  npy.minimum(self.py-1,1)
            self.az -=  npy.minimum(self.pz-1,1)

            # Fix the global indices
            if not self.zonal:
                self.nx -= npy.minimum(self.px-1,1)*self.px
                self.ny -= npy.minimum(self.py-1,1)*self.py
                self.nz -= npy.minimum(self.pz-1,1)*self.pz
            else:
                self.nx -= offsetx
                self.ny -= offsety
                self.nz -= offsetz

        self._domain_size = npy.array([self.nx,self.ny,self.nz])
                
        # Recomputed to fix actual count
        self.px = self.nx / self.ax
        self.py = self.ny / self.ay
        self.pz = self.nz / self.az

        self.nprocs = self.px * self.py * self.pz

        self.procs = {}
        ipp = 0
        for ipz in range(self.pz):
            for ipy in range(self.py):
                for ipx in range(self.px):
                    
                    gx1 = self.ax*ipx
                    gy1 = self.ay*ipy
                    gz1 = self.az*ipz

                    gxn = self.ax*(ipx+1)
                    gyn = self.ay*(ipy+1)
                    gzn = self.az*(ipz+1)
            
                    self.procs[ipp] = {}
                    self.procs[ipp]['g1'] = [gx1,gy1,gz1]
                    self.procs[ipp]['gn'] = [gxn,gyn,gzn]
                    
                    ipp += 1
                    

        self.varNames = []
        for var in self.plotDict['variables'][1:]:
            tmp = filter(None,var.split(' '))
            name = tmp[0]
            num  = int(tmp[1])
            if num > 1:
                for inum in range(num):
                    self.varNames.append( name+'-'+str(inum) )
            else:
                self.varNames.append( name )


        # Also include the materials if it exists
        if self.plotDict.has_key('materials'):
            for var in self.plotDict['materials'][1:]:
                tmp = filter(None,var.split(' '))
                name = tmp[0]
                num  = int(tmp[1])
                if num > 1:
                    for inum in range(num):
                        self.varNames.append( name+'-'+str(inum) )
                else:
                    self.varNames.append( name )

        self.nvars = len(self.varNames) 
        
        # Make timearray
        self.time = {}
        self._steps = []
        if self.plotDict.has_key('timesteps'):
            for tt in self.plotDict['timesteps'][1:]:
                tmp = filter(None,tt.split(' '))
                tindex = int(tmp[0])
                time  = float(tmp[1])
                self.time[tindex] = time
                self._steps.append( tindex )
        self.maxTimeIndex = npy.max( self.time.keys() )


        # Make a dictionary for lookups
        self.varDict = {}
        for ii in range(len(self.varNames)):
            name = self.varNames[ii]
            self.varDict[name] = ii
                
        
        self.dataFiles = os.path.dirname(self.plotMir) + '/' + self.plotDict['datafiles'][0]
        self.gridFiles = os.path.dirname(self.plotMir) + '/' + self.plotDict['gridfiles'][0]


        # Step is set to 0 by default.
        self._step = 0
        
   
        
    def setStep(self, step):
        """
        Update the metadata from the summary file in the data directory at a new time step.
        """
        
        assert (step in self._steps), "Step to read in is not available in the dataset."
        self._step = step
    
    
    def getStep(self):
        return self._step
    
    
    step = property(getStep, setStep)



    def setSubDomain(self, lo_and_hi):
        """
        Set the sub-domain for reading coordinates and data.
        """
        
        # Check if lo and hi are within the domain bounds first!!!
        
        try:
            lo, hi = lo_and_hi
        except ValueError:
            raise ValueError("Pass an iterable with two items!")
        
        for i in range(3):
            if lo[i] < 0 or lo[i] > self._domain_size[i]:
                raise ValueError('Invalid indices in chunk. Cannot be < 0 or > domain size!')
            if hi[i] < 0 or hi[i] > self._domain_size[i]:
                raise ValueError('Invalid indices in chunk. Cannot be < 0 or > domain size!')
            if hi[i] < lo[i]:
                raise ValueError('Invalid indices in chunk. Upper bound cannot be smaller than lower bound!')
        
        # Now set the chunk to be used later.
        self.chunk = ( (lo[0], hi[0] + 1), (lo[1], hi[1] + 1), (lo[2], hi[2] + 1) )
    

        
    def getSubDomain(self):
        """
        Return two tuples containing the sub-domain used in this reader
        as a lower bound (lo) and upper bound (hi).
        """
        
        lo = (self.chunk[0][0], self.chunk[1][0], self.chunk[2][0])
        hi = (self.chunk[0][1] - 1, self.chunk[1][1] - 1, self.chunk[2][1] - 1)
        
        return lo, hi
    
    
    sub_domain = property(getSubDomain, setSubDomain)


    @property
    def domain_size(self):
        """
        Return a tuple containing the full domain size of this dataset.
        """
        
        return tuple(self._domain_size)
    
    
    @property
    def dimension(self):
        """
        Return the dimension of the domain.
        """
        
        return 3
    
    
    @property
    def periodic_dimensions(self):
        """
        Return a tuple indicating if data is periodic in each dimension.
        """
        
        return (True, True, True)
    
    
    @property
    def time(self):
        """
        Return the simulation time at current time step.
        """
        
        return 0.
    
    
    @property
    def data_order(self):
        """
        Return the data order.
        """
        
        return 'F'
    
    @property
    def steps(self):
        """
        Return all of the steps.
        """
        
        return self._steps
    

    def readDataProc(self,time,proc,var_list ):
    
        # Take diff argument types
        for ivar in var_list:
            if ivar not in self.varDict.keys():
                print "%s not a valid variable" % ivar

        sdata = self.dataFiles % (time,proc)
        
        # Open fortran file
        fd = open(sdata,'rb')        
        data = npy.fromfile(file=fd,dtype=npy.single)      
        fd.close()

        # Return either list of arrays or single array
        vals = []
        for ivar in var_list:
            val = self.readDataProc_var( self.varDict[ivar] , proc, data) 
            vals.append( val )


        return vals


    def readDataProc_var(self,ivar, proc, data):

        # Ghost point in read
        ibx = self.xblk
        iby = self.yblk
        ibz = self.zblk

        shape = (self.az+ibz,self.ay+iby,self.ax+ibx)
        stride = npy.product(shape) + 2
           
        istart = ivar*stride + 1
        iend =  (ivar+1)*stride - 1            
        
        Vdata = data[istart:iend].reshape(shape)

        # Some logic
        sx = 0; ex = self.ax
        sy = 0; ey = self.ay        
        sz = 0; ez = self.az

        if (not self.legacy) and (not self.zonal):
            if ( (self.procs[proc]['gn'][0] == self.nx) and self.px > 1 ):
                sx += 1 
                ex += 1 

            if ( (self.procs[proc]['gn'][1] == self.ny) and self.py > 1 ):
                sy += 1 
                ey += 1 

            if ( (self.procs[proc]['gn'][2] == self.nz) and self.pz > 1 ):
                sz += 1 
                ez += 1 

            
        return npy.swapaxes(Vdata,0,2)[sx:ex,sy:ey,sz:ez]

      
    def readGridProc(self,proc):
        
        sdata = self.gridFiles % (proc)
        
        # Ghost point in read
        ibx = self.xblk
        iby = self.yblk
        ibz = self.zblk
 
        # Zonals have redundant data
        if self.zonal:
            if self.nx > 1:
                ibx += 1
            if self.ny > 1:
                iby += 1
            if self.nz > 1:
                ibz += 1
                
        # Open fortran file
        fd = open(sdata,'rb')        
        data = npy.fromfile(file=fd,dtype=npy.single)      

        shape = (self.az+ibz,self.ay+iby,self.ax+ibx)
        stride = npy.product(shape) + 2
            
        ivar = 0  # xgrid
        istart = ivar*stride + 1
        iend =  (ivar+1)*stride - 1            
        Xdata = data[istart:iend].reshape(shape)
        Xdata = npy.swapaxes(Xdata,0,2)
        
        ivar = 1  # ygrid
        istart = ivar*stride + 1
        iend =  (ivar+1)*stride - 1            
        Ydata = data[istart:iend].reshape(shape)
        Ydata = npy.swapaxes(Ydata,0,2)

        ivar = 2  # zgrid
        istart = ivar*stride + 1
        iend =  (ivar+1)*stride - 1            
        Zdata = data[istart:iend].reshape(shape)
        Zdata = npy.swapaxes(Zdata,0,2)

        # Zonal average in each direction
        if self.zonal:
            isx = int(self.nx > 1)
            isy = int(self.ny > 1)
            isz = int(self.nz > 1)
            if isx:
                Xdata = (Xdata[:-1,isy:,isz:] + Xdata[1:,isy:,isz:] ) / 2.0
            else:
                Xdata = Xdata[isx:,isy:,isz:]

            if isy:
                Ydata = (Ydata[isx:,:-1,isz:] + Ydata[isx:,1:,isz:] ) / 2.0
            else:
                Ydata = Ydata[isx:,isy:,isz:]

            if isz:
                Zdata = (Zdata[isx:,isy:,:-1] + Zdata[isx,isy:,1:] ) / 2.0
            else:
                Zdata = Zdata[isx:,isy:,isz:]



        # Some logic
        sx = 0; ex = self.ax
        sy = 0; ey = self.ay
        sz = 0; ez = self.az

        if not self.legacy  and (not self.zonal) :
            if ( (self.procs[proc]['gn'][0] == self.nx) and self.px > 1 ):
                sx += 1 
                ex += 1 

            if ( (self.procs[proc]['gn'][1] == self.ny) and self.py > 1 ):
                sy += 1 
                ey += 1 

            if ( (self.procs[proc]['gn'][2] == self.nz) and self.pz > 1 ):
                sz += 1 
                ez += 1
        
        return [Xdata[sx:ex,sy:ey,sz:ez] , Ydata[sx:ex,sy:ey,sz:ez] , Zdata[sx:ex,sy:ey,sz:ez]  ]


    def readGridChunk(self,irange):
        """
        Same as readData but only reads in global range of data given by
        irange.
        """


        Rx = [0]*2
        Ry = [0]*2
        Rz = [0]*2
        
        Rx[0] = irange[0]
        Rx[1] = irange[1]
        Ry[0] = irange[2]
        Ry[1] = irange[3]
        Rz[0] = irange[4]
        Rz[1] = irange[5]

        xx = npy.zeros( (Rx[1]-Rx[0],Ry[1]-Ry[0],Rz[1]-Rz[0]) )
        yy = npy.zeros( (Rx[1]-Rx[0],Ry[1]-Ry[0],Rz[1]-Rz[0]) )
        zz = npy.zeros( (Rx[1]-Rx[0],Ry[1]-Ry[0],Rz[1]-Rz[0]) )
        for iproc in range(self.nprocs):

            g1 = self.procs[iproc]['g1'] 
            gn = self.procs[iproc]['gn'] 
            
            # Shift left point if node data
            iff = 0;jff = 0;kff = 0;

            c1 = (Rx[1] in range(g1[0],gn[0]) )
            c2 = (Rx[0] in range(g1[0],gn[0]) )
            c3 = ( (g1[0] and gn[0]) in range(Rx[0],Rx[1]+1) )
            CX = c1 or c2 or c3

            c1 = (Ry[1] in range(g1[1],gn[1]) )
            c2 = (Ry[0] in range(g1[1],gn[1]) )
            c3 = ( (g1[1] and gn[1]) in range(Ry[0],Ry[1]+1) )
            CY = c1 or c2 or c3

            c1 = (Rz[1] in range(g1[2],gn[2]) )
            c2 = (Rz[0] in range(g1[2],gn[2]) )
            c3 = ( (g1[2] and gn[2]) in range(Rz[0],Rz[1]+1) )
            CZ = c1 or c2 or c3

            if ( CX and CY and CZ ):
                
                Li1 = npy.max( (0 , Rx[0] - g1[0] ) ) + iff
                Lif = npy.min( (Rx[1] , gn[0] ) ) - g1[0] + iff
                Ki1 = npy.max( (Rx[0] , g1[0]) ) - Rx[0]
                Kif = Ki1 + (Lif-Li1)

                Lj1 = npy.max( (0 , Ry[0] - g1[1] ) ) + jff
                Ljf = npy.min( (Ry[1] , gn[1] ) ) - g1[1] + jff
                Kj1 = npy.max( (Ry[0] , g1[1]) ) - Ry[0]
                Kjf = Kj1 + (Ljf-Lj1)

                Lk1 = npy.max( (0 , Rz[0] - g1[2] ) ) + kff
                Lkf = npy.min( (Rz[1] , gn[2] ) ) - g1[2] + kff
                Kk1 = npy.max( (Rz[0] , g1[2]) ) - Rz[0]
                Kkf = Kk1 + (Lkf-Lk1)
                
                [x,y,z] = self.readGridProc(iproc)
            
                xx[Ki1:Kif,Kj1:Kjf,Kk1:Kkf] = x[Li1:Lif,Lj1:Ljf,Lk1:Lkf]
                yy[Ki1:Kif,Kj1:Kjf,Kk1:Kkf] = y[Li1:Lif,Lj1:Ljf,Lk1:Lkf]
                zz[Ki1:Kif,Kj1:Kjf,Kk1:Kkf] = z[Li1:Lif,Lj1:Ljf,Lk1:Lkf]


        return [xx,yy,zz]

    
    
    def readCoordinates(self):
        """
        Method to read in the X, Y and Z coordinates of a chunk of index values.
        """
        irange = [self.chunk[0][0],self.chunk[0][1],
                  self.chunk[1][0],self.chunk[1][1],
                  self.chunk[2][0],self.chunk[2][1]]

        [x,y,z] = self.readGridChunk(irange)
        return x , y , z

    
    def readChunk(self,time,variable,irange):
        """
        Same as readData but only reads in global range of data given by
        irange.
        """

        # Make them all lists
        if type(variable) == type('foo'):
            variable = [ variable ]

        Rx = [0]*2
        Ry = [0]*2
        Rz = [0]*2
        
        Rx[0] = irange[0]
        Rx[1] = irange[1]
        Ry[0] = irange[2]
        Ry[1] = irange[3]
        Rz[0] = irange[4]
        Rz[1] = irange[5]

        vdata = []
        for ii in range(len(variable)):
            vdata.append( npy.zeros( (Rx[1]-Rx[0],Ry[1]-Ry[0],Rz[1]-Rz[0]) ) )

        for iproc in range(self.nprocs):

            g1 = self.procs[iproc]['g1'] 
            gn = self.procs[iproc]['gn'] 
            
            # Shift left point if node data
            iff = 0;jff = 0;kff = 0;

            c1 = (Rx[1] in range(g1[0],gn[0]) )
            c2 = (Rx[0] in range(g1[0],gn[0]) )
            c3 = ( (g1[0] and gn[0]) in range(Rx[0],Rx[1]+1) )
            CX = c1 or c2 or c3

            c1 = (Ry[1] in range(g1[1],gn[1]) )
            c2 = (Ry[0] in range(g1[1],gn[1]) )
            c3 = ( (g1[1] and gn[1]) in range(Ry[0],Ry[1]+1) )
            CY = c1 or c2 or c3

            c1 = (Rz[1] in range(g1[2],gn[2]) )
            c2 = (Rz[0] in range(g1[2],gn[2]) )
            c3 = ( (g1[2] and gn[2]) in range(Rz[0],Rz[1]+1) )
            CZ = c1 or c2 or c3

            if ( CX and CY and CZ ):
                
                Li1 = npy.max( (0 , Rx[0] - g1[0] ) ) + iff
                Lif = npy.min( (Rx[1] , gn[0] ) ) - g1[0] + iff
                Ki1 = npy.max( (Rx[0] , g1[0]) ) - Rx[0]
                Kif = Ki1 + (Lif-Li1)

                Lj1 = npy.max( (0 , Ry[0] - g1[1] ) ) + jff
                Ljf = npy.min( (Ry[1] , gn[1] ) ) - g1[1] + jff
                Kj1 = npy.max( (Ry[0] , g1[1]) ) - Ry[0]
                Kjf = Kj1 + (Ljf-Lj1)

                Lk1 = npy.max( (0 , Rz[0] - g1[2] ) ) + kff
                Lkf = npy.min( (Rz[1] , gn[2] ) ) - g1[2] + kff
                Kk1 = npy.max( (Rz[0] , g1[2]) ) - Rz[0]
                Kkf = Kk1 + (Lkf-Lk1)
                
                pdata = self.readDataProc(time,iproc,variable)
            
                for ii in range(len(variable)):
                    vdata[ii][Ki1:Kif,Kj1:Kjf,Kk1:Kkf] = pdata[ii][Li1:Lif,Lj1:Ljf,Lk1:Lkf]

        # Return non-list
        if len(variable) == 1:
            return vdata[0]
        else:
            return vdata

    
    def readData(self, var_names, data=None):
        """
        Method to read in the a chunk of the data for variables at current vizdump step.
        """

        irange = [self.chunk[0][0],self.chunk[0][1],
                  self.chunk[1][0],self.chunk[1][1],
                  self.chunk[2][0],self.chunk[2][1]]

        variable = var_name
        time = self._step
        
        data = self.readChunk(time,variable,irange)

        return data


BaseReader.register(MirandaReader)

if __name__ == '__main__':
    print 'Subclass:', issubclass(MirandaReader, BaseReader)
    print 'Instance:', isinstance(MirandaReader("../tests/test_data_miranda/RM_CTR_3D_64/plot.mir"), BaseReader)
